"""SQLAlchemy ORM models for BlackBoxAF pattern storage."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    """Represents an ingested SFDX project (anonymized)."""

    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_hash = Column(String(12), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    project_path = Column(Text, nullable=False)
    ingested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    pattern_count = Column(Integer, default=0)
    metadata_counts = Column(Text, default="{}")  # JSON string

    patterns = relationship("Pattern", back_populates="source", cascade="all, delete-orphan")

    def set_metadata_counts(self, counts: dict):
        self.metadata_counts = json.dumps(counts)

    def get_metadata_counts(self) -> dict:
        return json.loads(self.metadata_counts or "{}")


class Pattern(Base):
    """A single extracted metadata pattern."""

    __tablename__ = "patterns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_type = Column(String(50), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    source_object = Column(String(100), default="Unknown", index=True)
    structure = Column(Text, nullable=False)  # JSON
    field_references = Column(Text, default="[]")  # JSON array
    api_version = Column(String(10), default="")
    complexity_score = Column(Integer, default=1, index=True)
    tags = Column(Text, default="")  # Comma-separated for FTS, JSON for querying
    source_hash = Column(String(12), nullable=False)
    source_file = Column(String(200), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    favorited = Column(Boolean, default=False)
    use_count = Column(Integer, default=0)

    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    source = relationship("Source", back_populates="patterns")

    __table_args__ = (
        Index("idx_pattern_category_type", "category", "pattern_type"),
        Index("idx_pattern_source", "source_hash"),
        Index("idx_pattern_complexity", "complexity_score"),
    )

    def set_structure(self, data: dict):
        self.structure = json.dumps(data)

    def get_structure(self) -> dict:
        return json.loads(self.structure or "{}")

    def set_field_references(self, refs: list[str]):
        self.field_references = json.dumps(refs)

    def get_field_references(self) -> list[str]:
        return json.loads(self.field_references or "[]")

    def set_tags(self, tag_list: list[str]):
        self.tags = json.dumps(tag_list)

    def get_tags(self) -> list[str]:
        try:
            return json.loads(self.tags or "[]")
        except json.JSONDecodeError:
            return []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pattern_type": self.pattern_type,
            "category": self.category,
            "name": self.name,
            "description": self.description,
            "source_object": self.source_object,
            "structure": self.get_structure(),
            "field_references": self.get_field_references(),
            "api_version": self.api_version,
            "complexity_score": self.complexity_score,
            "tags": self.get_tags(),
            "source_hash": self.source_hash,
            "source_file": self.source_file,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "favorited": self.favorited,
            "use_count": self.use_count,
        }

    def to_summary(self) -> dict:
        """Lightweight dict for grid/list views."""
        return {
            "id": self.id,
            "pattern_type": self.pattern_type,
            "category": self.category,
            "name": self.name,
            "description": self.description,
            "source_object": self.source_object,
            "complexity_score": self.complexity_score,
            "tags": self.get_tags(),
            "favorited": self.favorited,
            "use_count": self.use_count,
        }
