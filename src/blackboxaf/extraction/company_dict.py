"""Company name dictionary for enhanced brand detection.

Loads a pre-built dictionary of known company, government, education,
and nonprofit organization names from public sources (SEC EDGAR,
Fortune 1000, US federal agencies). Used as an additional detection
layer alongside the heuristic CamelCase brand detection.

Sources (all public data):
- SEC EDGAR company_tickers.json (~10K publicly traded companies)
- Fortune 500/1000 CSV (top US companies by revenue)
- CISA dotgov-data (US federal agencies)

The dictionary file (company_names.txt) is pre-built by running:
    python -m blackboxaf.extraction.build_company_db
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"
_DICT_FILE = _DATA_DIR / "company_names.txt"

# Cached dictionary (loaded once per process)
_company_names: set[str] | None = None

# Words that are too generic to flag on their own even if they match
# a company name. These require additional context (like appearing
# as a field prefix across multiple objects) to be flagged.
_TOO_COMMON_ALONE = {
    # Real company names that are also common English words
    "apple", "oracle", "target", "delta", "uber", "snap", "block",
    "square", "unity", "match", "dish", "visa", "ford", "shell",
    "cardinal", "frontier", "summit", "pinnacle", "global", "national",
    "american", "united", "premier", "standard", "general", "liberty",
    "patriot", "guardian", "advance", "progressive", "select", "prime",
    "universal", "allied", "pacific", "atlantic", "southern", "northern",
    "western", "eastern", "central", "mutual", "trust", "fidelity",
    "pioneer", "quest", "genesis", "spark", "relay", "pulse", "core",
    "vertex", "apex", "nexus", "harbor", "beacon", "bridge", "compass",
    "insight", "horizon", "catalyst", "terra", "nova", "spectrum",
    "resolve", "charter", "century", "diamond", "sterling", "marathon",
    "tribune", "merit", "legacy",
    # Common Salesforce / CRM field words
    "status", "custom", "direct", "form", "field", "record", "report",
    "contact", "account", "order", "product", "asset", "quote", "value",
    "source", "owner", "parent", "active", "total", "amount", "score",
    "action", "event", "alert", "update", "create", "review", "submit",
    "access", "share", "public", "current", "complete", "region",
    "response", "request", "notice", "renewal", "invoice", "payment",
    "credit", "balance", "limit", "impact", "connect", "focus",
    "engage", "encore", "integrity", "express", "pilot",
    "contract", "vendor", "partner", "client", "prospect", "campaign",
    "batch", "schedule", "trigger", "method", "process", "workflow",
    "origin", "type", "lead", "case", "task", "note", "role",
}

# Minimum length for dictionary matches (shorter = too many false positives)
_MIN_MATCH_LENGTH = 4


def load_company_dict() -> set[str]:
    """Load the company names dictionary from disk.

    Returns a set of lowercase company name strings.
    Caches the result for subsequent calls.
    """
    global _company_names

    if _company_names is not None:
        return _company_names

    if not _DICT_FILE.exists():
        logger.warning(
            f"Company dictionary not found at {_DICT_FILE}. "
            "Run 'python -m blackboxaf.extraction.build_company_db' to build it. "
            "Dictionary-based brand detection will be skipped."
        )
        _company_names = set()
        return _company_names

    names = set()
    with open(_DICT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if name and not name.startswith("#"):
                names.add(name)

    _company_names = names
    logger.info(f"Loaded company dictionary: {len(names)} names")
    return _company_names


def is_known_company(term: str) -> bool:
    """Check if a term matches a known company/organization name.

    Args:
        term: The term to check (e.g., a field name segment)

    Returns:
        True if the term matches a known company name and is
        specific enough to flag (not in the too-common list).
    """
    if len(term) < _MIN_MATCH_LENGTH:
        return False

    names = load_company_dict()
    if not names:
        return False

    lower = term.lower()

    # Skip terms that are too generic on their own
    if lower in _TOO_COMMON_ALONE:
        return False

    return lower in names


def find_company_matches(field_segments: list[str]) -> list[str]:
    """Find company name matches in a list of field name segments.

    Checks individual segments and also tries combining adjacent
    segments (e.g., "Direct" + "Energy" -> "direct energy").

    Args:
        field_segments: List of segments from splitting a field name
                       on underscores (e.g., ["Direct", "Energy", "Status"])

    Returns:
        List of matched company name strings.
    """
    names = load_company_dict()
    if not names:
        return []

    matches = []

    # Check individual segments
    for seg in field_segments:
        if len(seg) >= _MIN_MATCH_LENGTH and is_known_company(seg):
            matches.append(seg)

    # Check 2-word combinations (e.g., "Direct_Energy" -> "direct energy")
    for i in range(len(field_segments) - 1):
        combined = f"{field_segments[i]} {field_segments[i + 1]}".lower()
        if combined in names and combined not in _TOO_COMMON_ALONE:
            # Return the original casing joined
            matches.append(f"{field_segments[i]}_{field_segments[i + 1]}")

    # Check 3-word combinations (e.g., "PR_News_Wire")
    for i in range(len(field_segments) - 2):
        combined = (
            f"{field_segments[i]} {field_segments[i + 1]} "
            f"{field_segments[i + 2]}"
        ).lower()
        if combined in names and combined not in _TOO_COMMON_ALONE:
            matches.append(
                f"{field_segments[i]}_{field_segments[i + 1]}_"
                f"{field_segments[i + 2]}"
            )

    return matches


def get_dict_stats() -> dict:
    """Get statistics about the loaded dictionary."""
    names = load_company_dict()
    return {
        "total_names": len(names),
        "dict_file": str(_DICT_FILE),
        "dict_exists": _DICT_FILE.exists(),
        "too_common_excluded": len(_TOO_COMMON_ALONE),
        "min_match_length": _MIN_MATCH_LENGTH,
    }
