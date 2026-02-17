"""API routes for querying and managing patterns."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, text

from ..config import CATEGORY_COLORS
from ..db.database import get_session_factory, init_db
from ..db.models import Pattern, Source

router = APIRouter(prefix="/api", tags=["patterns"])


@router.get("/patterns")
async def list_patterns(
    category: str | None = None,
    pattern_type: str | None = None,
    source_object: str | None = None,
    min_complexity: int | None = None,
    max_complexity: int | None = None,
    favorited: bool | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    """List patterns with filtering, search, and pagination."""
    engine = init_db()
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        query = session.query(Pattern)

        # Apply filters
        if category:
            query = query.filter(Pattern.category == category)
        if pattern_type:
            query = query.filter(Pattern.pattern_type == pattern_type)
        if source_object:
            query = query.filter(Pattern.source_object == source_object)
        if min_complexity is not None:
            query = query.filter(Pattern.complexity_score >= min_complexity)
        if max_complexity is not None:
            query = query.filter(Pattern.complexity_score <= max_complexity)
        if favorited is not None:
            query = query.filter(Pattern.favorited == favorited)

        # Full-text search
        if q:
            # Use FTS5 for search
            fts_ids = session.execute(
                text("SELECT row_id FROM patterns_fts WHERE patterns_fts MATCH :q"),
                {"q": q},
            ).fetchall()
            matching_ids = [row[0] for row in fts_ids]
            if matching_ids:
                query = query.filter(Pattern.id.in_(matching_ids))
            else:
                # Fallback to LIKE search
                like_q = f"%{q}%"
                query = query.filter(
                    (Pattern.name.ilike(like_q))
                    | (Pattern.description.ilike(like_q))
                    | (Pattern.source_object.ilike(like_q))
                )

        total = query.count()
        patterns = (
            query
            .order_by(Pattern.complexity_score.desc(), Pattern.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
            "patterns": [p.to_summary() for p in patterns],
        }


@router.get("/patterns/{pattern_id}")
async def get_pattern(pattern_id: int):
    """Get full pattern detail including structure."""
    engine = init_db()
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        pattern = session.query(Pattern).filter_by(id=pattern_id).first()
        if not pattern:
            raise HTTPException(status_code=404, detail="Pattern not found")
        return pattern.to_dict()


@router.post("/patterns/{pattern_id}/favorite")
async def toggle_favorite(pattern_id: int):
    """Toggle favorite status on a pattern."""
    engine = init_db()
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        pattern = session.query(Pattern).filter_by(id=pattern_id).first()
        if not pattern:
            raise HTTPException(status_code=404, detail="Pattern not found")
        pattern.favorited = not pattern.favorited
        session.commit()
        return {"id": pattern_id, "favorited": pattern.favorited}


@router.get("/stats")
async def get_stats():
    """Get dashboard statistics."""
    engine = init_db()
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        total = session.query(Pattern).count()

        # Count by category
        by_category = (
            session.query(Pattern.category, func.count(Pattern.id))
            .group_by(Pattern.category)
            .all()
        )

        # Count by pattern type
        by_type = (
            session.query(Pattern.pattern_type, func.count(Pattern.id))
            .group_by(Pattern.pattern_type)
            .all()
        )

        # Count by source object (top 20)
        by_object = (
            session.query(Pattern.source_object, func.count(Pattern.id))
            .group_by(Pattern.source_object)
            .order_by(func.count(Pattern.id).desc())
            .limit(20)
            .all()
        )

        # Complexity distribution
        by_complexity = (
            session.query(Pattern.complexity_score, func.count(Pattern.id))
            .group_by(Pattern.complexity_score)
            .all()
        )

        # Sources
        sources = session.query(Source).all()

        return {
            "total_patterns": total,
            "by_category": [
                {"category": cat, "count": count, "color": CATEGORY_COLORS.get(cat, "#888")}
                for cat, count in by_category
            ],
            "by_type": [
                {"type": t, "count": c} for t, c in by_type
            ],
            "by_object": [
                {"object": obj, "count": c} for obj, c in by_object
            ],
            "by_complexity": [
                {"score": score, "count": c} for score, c in by_complexity
            ],
            "sources": [
                {
                    "name": s.display_name,
                    "hash": s.source_hash,
                    "pattern_count": s.pattern_count,
                    "ingested_at": s.ingested_at.isoformat() if s.ingested_at else None,
                }
                for s in sources
            ],
        }


@router.get("/filters")
async def get_filter_options():
    """Get available filter values for the UI dropdowns."""
    engine = init_db()
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        categories = [
            row[0] for row in
            session.query(Pattern.category).distinct().order_by(Pattern.category).all()
        ]
        pattern_types = [
            row[0] for row in
            session.query(Pattern.pattern_type).distinct().order_by(Pattern.pattern_type).all()
        ]
        objects = [
            row[0] for row in
            session.query(Pattern.source_object).distinct().order_by(Pattern.source_object).all()
        ]

        return {
            "categories": categories,
            "pattern_types": pattern_types,
            "objects": objects,
            "colors": CATEGORY_COLORS,
        }


# ── LLM-powered natural language search ──

@router.post('/patterns/search/nl')
async def search_nl(query: str):
    """Natural language pattern search.
    
    Example: POST /api/patterns/search/nl?query=approval flows with email notification
    
    Returns: List of pattern IDs matching the query, ordered by relevance.
    
    Cost: ~$0.001-0.003 per search (Claude Haiku). Cached for 24 hours.
    Daily limit: $1.00 to prevent runaway costs.
    """
    from .llm import search_patterns_nl
    
    engine = init_db()
    session_factory = get_session_factory(engine)
    
    with session_factory() as session:
        # Get all patterns (summary only)
        patterns = session.query(Pattern).all()
        pattern_summaries = [p.to_summary() for p in patterns]
        
        # Call LLM search
        pattern_ids = await search_patterns_nl(query, pattern_summaries)
        
        # Fetch full patterns
        if pattern_ids:
            results = session.query(Pattern).filter(
                Pattern.id.in_(pattern_ids)
            ).all()
            # Sort by the order returned by LLM
            id_to_pattern = {p.id: p for p in results}
            sorted_patterns = [id_to_pattern[pid] for pid in pattern_ids if pid in id_to_pattern]
            return {
                'results': [p.to_summary() for p in sorted_patterns],
                'total': len(sorted_patterns),
                'query': query,
                'method': 'llm',
            }
        else:
            return {
                'results': [],
                'total': 0,
                'query': query,
                'method': 'llm',
            }


@router.get('/patterns/search/cost')
async def get_search_cost():
    """Get today's LLM search API costs."""
    from .llm import get_daily_cost
    return {'daily_cost': get_daily_cost(), 'limit': 1.00}

