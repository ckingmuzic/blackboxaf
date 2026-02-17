"""SQLite database setup and session management."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from ..config import DB_PATH
from .models import Base


def get_engine(db_path: Path | None = None):
    """Create a SQLAlchemy engine for the SQLite database."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        f"sqlite:///{path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Enable WAL mode and foreign keys
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def init_db(engine=None):
    """Initialize the database, creating tables if needed."""
    if engine is None:
        engine = get_engine()

    Base.metadata.create_all(engine)

    # Migrate: add new columns if they don't exist (safe to re-run)
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE patterns ADD COLUMN content_hash VARCHAR(16)"
            ))
            conn.commit()
        except Exception:
            conn.rollback()
        try:
            conn.execute(text(
                "ALTER TABLE patterns ADD COLUMN seen_in_sources TEXT DEFAULT '[]'"
            ))
            conn.commit()
        except Exception:
            conn.rollback()

    # Create standalone FTS5 virtual table (not content-synced)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS patterns_fts USING fts5(
                name,
                description,
                tags,
                source_object,
                pattern_type,
                row_id UNINDEXED
            )
        """))
        conn.commit()

    return engine


def get_session_factory(engine=None) -> sessionmaker:
    """Get a session factory bound to the engine."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)


def rebuild_fts(session: Session):
    """Rebuild the FTS index from the patterns table."""
    session.execute(text("DELETE FROM patterns_fts"))
    session.execute(text("""
        INSERT INTO patterns_fts(name, description, tags, source_object, pattern_type, row_id)
        SELECT name, description, tags, source_object, pattern_type, id
        FROM patterns
    """))
    session.commit()
