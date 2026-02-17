"""LLM-powered natural language search for patterns.

Cost optimization:
- Caches responses for 24 hours (same query = free second time)
- Limits pattern context to summaries (not full structures)
- Uses Claude Haiku for searches (10x cheaper than Sonnet)
- Rate-limited to prevent cost runaway
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import HTTPException

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# Cost tracking
_CACHE_DIR = Path.home() / ".blackboxaf" / "llm_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_COST_PER_1M_INPUT = 0.25  # Claude Haiku: $0.25 per 1M input tokens
_COST_PER_1M_OUTPUT = 1.25  # Claude Haiku: $1.25 per 1M output tokens
_MAX_DAILY_COST = 1.00  # Max $1/day in API costs


def _get_cache_path(query_hash: str) -> Path:
    return _CACHE_DIR / f"{query_hash}.json"


def _cache_key(query: str, pattern_count: int) -> str:
    """Generate cache key from query + pattern count."""
    return hashlib.md5(f"{query}:{pattern_count}".encode()).hexdigest()


def _load_cache(cache_key: str) -> dict | None:
    """Load cached response if it exists and is < 24 hours old."""
    cache_path = _get_cache_path(cache_key)
    if not cache_path.exists():
        return None

    try:
        with open(cache_path) as f:
            cached = json.load(f)

        # Check if cache is still valid (24 hours)
        cached_time = datetime.fromisoformat(cached["timestamp"])
        if datetime.now() - cached_time < timedelta(hours=24):
            return cached
    except (json.JSONDecodeError, KeyError, ValueError):
        pass

    return None


def _save_cache(cache_key: str, result: dict):
    """Save response to cache."""
    cache_path = _get_cache_path(cache_key)
    with open(cache_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "result": result,
        }, f)


def _track_cost(input_tokens: int, output_tokens: int) -> float:
    """Track daily API costs and enforce limits."""
    cost = (
        (input_tokens / 1_000_000) * _COST_PER_1M_INPUT +
        (output_tokens / 1_000_000) * _COST_PER_1M_OUTPUT
    )

    # Load today's costs
    cost_file = _CACHE_DIR / f"cost_{datetime.now().strftime('%Y-%m-%d')}.txt"
    daily_cost = 0.0
    if cost_file.exists():
        try:
            daily_cost = float(cost_file.read_text())
        except ValueError:
            pass

    # Check limit
    if daily_cost + cost > _MAX_DAILY_COST:
        raise HTTPException(
            status_code=429,
            detail=f"Daily LLM cost limit reached (${_MAX_DAILY_COST:.2f}). Try again tomorrow or use keyword search."
        )

    # Update cost
    with open(cost_file, "w") as f:
        f.write(str(daily_cost + cost))

    return cost


async def search_patterns_nl(
    query: str,
    patterns: list[dict[str, Any]],
) -> list[int]:
    """Search patterns using natural language.

    Args:
        query: Natural language query (e.g., "approval flows with email notification")
        patterns: List of pattern summary dicts (id, name, description, tags, category)

    Returns:
        List of pattern IDs that match the query, sorted by relevance

    Raises:
        HTTPException: If Anthropic API key not set or daily cost limit exceeded
    """
    if not ANTHROPIC_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="LLM features require the 'anthropic' package. Install with: pip install anthropic"
        )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="LLM search requires ANTHROPIC_API_KEY environment variable. Get one at: https://console.anthropic.com/"
        )

    # Check cache first
    cache_key = _cache_key(query, len(patterns))
    cached = _load_cache(cache_key)
    if cached:
        return cached["result"]["pattern_ids"]

    # Build prompt with pattern summaries (not full structures - saves tokens)
    pattern_summaries = []
    for p in patterns[:100]:  # Limit to first 100 to control costs
        pattern_summaries.append(
            f"ID {p['id']}: {p['name']} | {p['category']} | "
            f"Tags: {', '.join(p.get('tags', [])[:5])} | "
            f"Complexity: {p.get('complexity_score', 0)}"
        )

    prompt = f"""You are a Salesforce pattern search assistant.

User query: "{query}"

Available patterns (ID, name, category, tags, complexity):
{chr(10).join(pattern_summaries[:50])}

Respond ONLY with a JSON array of pattern IDs that best match the query, ordered by relevance.
Return at most 10 IDs. If no patterns match, return an empty array.

Example response: [42, 17, 93, 8]

Your response:"""

    # Call Claude API (Haiku for low cost)
    client = Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",  # Cheapest model
            max_tokens=256,  # Short response = low cost
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Claude API error: {str(e)}"
        )

    # Track cost
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = _track_cost(input_tokens, output_tokens)

    # Parse response
    response_text = response.content[0].text.strip()

    try:
        # Try to extract JSON array from response
        if "[" in response_text and "]" in response_text:
            start = response_text.index("[")
            end = response_text.rindex("]") + 1
            pattern_ids = json.loads(response_text[start:end])
        else:
            pattern_ids = []

        # Validate IDs
        valid_ids = [p["id"] for p in patterns]
        pattern_ids = [pid for pid in pattern_ids if pid in valid_ids]

    except (json.JSONDecodeError, ValueError):
        # Fallback: keyword search
        pattern_ids = []

    result = {
        "pattern_ids": pattern_ids,
        "cost": cost,
        "tokens": {"input": input_tokens, "output": output_tokens},
    }

    # Cache result
    _save_cache(cache_key, result)

    return pattern_ids


def get_daily_cost() -> float:
    """Get today's LLM API costs."""
    cost_file = _CACHE_DIR / f"cost_{datetime.now().strftime('%Y-%m-%d')}.txt"
    if cost_file.exists():
        try:
            return float(cost_file.read_text())
        except ValueError:
            pass
    return 0.0


def clear_cache():
    """Clear all cached responses (for testing/debugging)."""
    for cache_file in _CACHE_DIR.glob("*.json"):
        cache_file.unlink()
