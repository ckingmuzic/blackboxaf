"""API routes for ingesting SFDX projects."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db.database import get_session_factory, init_db, rebuild_fts
from ..db.models import Pattern, Source
from ..extraction.scanner import ScanProgress, list_sfdx_projects, scan_sfdx_project

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ingest"])

# Track active ingestion state
_ingest_status: dict[str, ScanProgress] = {}


class IngestRequest(BaseModel):
    path: str
    brand_terms: list[str] | None = None  # Custom terms to scrub (e.g. ["AcmeCloud", "WidgetCo"])


class IngestResponse(BaseModel):
    source_id: str
    source_hash: str
    patterns_found: int
    duplicates_skipped: int = 0
    metadata_counts: dict[str, int]
    errors: list[str]


class ProjectInfo(BaseModel):
    name: str
    path: str
    has_sfdx_config: bool
    has_force_app: bool


@router.post("/ingest", response_model=IngestResponse)
async def ingest_project(request: IngestRequest):
    """Ingest an SFDX project directory and extract patterns."""
    project_path = Path(request.path)

    if not project_path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {request.path}")

    if not project_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.path}")

    # Run scan in thread pool to avoid blocking
    loop = asyncio.get_event_loop()

    def on_progress(progress: ScanProgress):
        _ingest_status[request.path] = progress

    result = await loop.run_in_executor(
        None,
        lambda: scan_sfdx_project(
            project_path,
            progress_callback=on_progress,
            custom_brand_terms=request.brand_terms,
        ),
    )

    if not result.patterns:
        return IngestResponse(
            source_id=result.source_id,
            source_hash=result.source_hash,
            patterns_found=0,
            metadata_counts=result.progress.metadata_counts,
            errors=result.progress.errors or ["No patterns found. Is this an SFDX project?"],
        )

    # Store in database
    engine = init_db()
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        # Create or update source record
        existing_source = session.query(Source).filter_by(
            source_hash=result.source_hash
        ).first()

        if existing_source:
            # Remove old patterns from this source
            session.query(Pattern).filter_by(source_id=existing_source.id).delete()
            source = existing_source
            source.pattern_count = len(result.patterns)
            source.set_metadata_counts(result.progress.metadata_counts)
        else:
            source = Source(
                source_hash=result.source_hash,
                display_name=result.source_id,
                project_path=str(project_path),
                pattern_count=len(result.patterns),
            )
            source.set_metadata_counts(result.progress.metadata_counts)
            session.add(source)
            session.flush()

        # Insert patterns, deduplicating across sources
        inserted = 0
        duplicates = 0

        for extracted in result.patterns:
            content_hash = Pattern.compute_content_hash(
                extracted.pattern_type,
                extracted.source_object,
                extracted.structure,
            )

            # Check if an identical pattern already exists from another source
            existing = session.query(Pattern).filter_by(
                content_hash=content_hash
            ).first()

            if existing and existing.source_hash != result.source_hash:
                # Duplicate from another source — just record provenance
                existing.add_seen_source(result.source_hash)
                duplicates += 1
                continue

            pattern = Pattern(
                pattern_type=extracted.pattern_type,
                category=extracted.category,
                name=extracted.name,
                description=extracted.description,
                source_object=extracted.source_object,
                complexity_score=extracted.complexity_score,
                api_version=extracted.api_version,
                source_hash=extracted.source_hash,
                source_file=extracted.source_file,
                source_id=source.id,
                content_hash=content_hash,
                seen_in_sources=json.dumps([result.source_hash]),
            )
            pattern.set_structure(extracted.structure)
            pattern.set_field_references(extracted.field_references)
            pattern.set_tags(extracted.tags)
            session.add(pattern)
            inserted += 1

        source.pattern_count = inserted
        session.commit()

        # Rebuild FTS index
        rebuild_fts(session)

    # Clean up progress
    _ingest_status.pop(request.path, None)

    return IngestResponse(
        source_id=result.source_id,
        source_hash=result.source_hash,
        patterns_found=inserted,
        duplicates_skipped=duplicates,
        metadata_counts=result.progress.metadata_counts,
        errors=result.progress.errors,
    )


@router.get("/ingest/status")
async def ingest_status():
    """Get current ingestion progress."""
    statuses = {}
    for path, progress in _ingest_status.items():
        statuses[path] = {
            "total_files": progress.total_files,
            "processed_files": progress.processed_files,
            "patterns_found": progress.patterns_found,
            "current_file": progress.current_file,
            "percent": round(progress.percent, 1),
        }
    return statuses


@router.get("/projects", response_model=list[ProjectInfo])
async def list_projects(base_path: str = ""):
    """List available SFDX projects in a directory."""
    projects = list_sfdx_projects(base_path)
    return [ProjectInfo(**p) for p in projects]


@router.post("/dedup")
async def deduplicate_patterns():
    """Find and remove duplicate patterns already in the database.

    Computes content_hash for any rows missing it, then removes
    duplicates keeping the oldest row and merging seen_in_sources.
    """
    engine = init_db()
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        # Step 1: Backfill content_hash for existing rows that lack it
        unhashed = session.query(Pattern).filter(
            (Pattern.content_hash == None) | (Pattern.content_hash == "")  # noqa: E711
        ).all()

        backfilled = 0
        for p in unhashed:
            p.content_hash = Pattern.compute_content_hash(
                p.pattern_type, p.source_object, p.get_structure()
            )
            if not p.seen_in_sources or p.seen_in_sources == "[]":
                p.seen_in_sources = json.dumps([p.source_hash])
            backfilled += 1

        if backfilled:
            session.flush()

        # Step 2: Find duplicate groups (same content_hash, multiple rows)
        from sqlalchemy import func
        dupes = (
            session.query(Pattern.content_hash, func.count(Pattern.id))
            .filter(Pattern.content_hash != None)  # noqa: E711
            .group_by(Pattern.content_hash)
            .having(func.count(Pattern.id) > 1)
            .all()
        )

        removed = 0
        for content_hash, count in dupes:
            # Get all patterns with this hash, oldest first
            group = (
                session.query(Pattern)
                .filter_by(content_hash=content_hash)
                .order_by(Pattern.created_at.asc())
                .all()
            )

            # Keep the first (oldest), merge provenance from others
            keeper = group[0]
            for dup in group[1:]:
                # Merge seen_in_sources
                for src in dup.get_seen_in_sources():
                    keeper.add_seen_source(src)
                # Preserve favorites and use_count
                if dup.favorited:
                    keeper.favorited = True
                keeper.use_count += dup.use_count
                session.delete(dup)
                removed += 1

        session.commit()
        rebuild_fts(session)

    return {
        "backfilled_hashes": backfilled,
        "duplicates_removed": removed,
        "duplicate_groups": len(dupes),
    }
