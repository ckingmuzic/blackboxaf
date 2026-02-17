"""Base classes for metadata extraction."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Salesforce metadata XML namespace
SF_NS = "http://soap.sforce.com/2006/04/metadata"
NS = {"sf": SF_NS}


def sf_tag(tag: str) -> str:
    """Return a fully-qualified Salesforce namespace tag."""
    return f"{{{SF_NS}}}{tag}"


def find_text(element: ET.Element, tag: str, default: str = "") -> str:
    """Find text content of a child element, namespace-aware."""
    child = element.find(sf_tag(tag))
    return child.text.strip() if child is not None and child.text else default


def find_all(element: ET.Element, tag: str) -> list[ET.Element]:
    """Find all child elements with the given tag, namespace-aware."""
    return element.findall(sf_tag(tag))


def element_to_dict(element: ET.Element) -> dict[str, Any]:
    """Recursively convert an XML element to a dict, stripping namespaces."""
    tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
    result: dict[str, Any] = {}

    # Attributes (rare in SF metadata but possible)
    if element.attrib:
        result["@attrs"] = dict(element.attrib)

    children = list(element)
    if not children:
        # Leaf node - return text content
        return {tag: element.text.strip() if element.text else ""}

    # Group children by tag name
    child_groups: dict[str, list] = {}
    for child in children:
        child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        child_groups.setdefault(child_tag, []).append(child)

    for child_tag, group in child_groups.items():
        if len(group) == 1:
            child = group[0]
            if list(child):
                result[child_tag] = element_to_dict(child).get(child_tag, {})
            else:
                result[child_tag] = child.text.strip() if child.text else ""
        else:
            result[child_tag] = []
            for child in group:
                if list(child):
                    result[child_tag].append(element_to_dict(child).get(child_tag, {}))
                else:
                    result[child_tag].append(child.text.strip() if child.text else "")

    return {tag: result}


@dataclass
class ExtractedPattern:
    """A single extracted, anonymized metadata pattern."""

    pattern_type: str
    category: str
    name: str
    description: str
    source_object: str
    structure: dict[str, Any]
    field_references: list[str]
    api_version: str
    complexity_score: int
    tags: list[str] = field(default_factory=list)
    source_hash: str = ""
    source_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "pattern_type": self.pattern_type,
            "category": self.category,
            "name": self.name,
            "description": self.description,
            "source_object": self.source_object,
            "structure": self.structure,
            "field_references": self.field_references,
            "api_version": self.api_version,
            "complexity_score": self.complexity_score,
            "tags": self.tags,
            "source_hash": self.source_hash,
            "source_file": self.source_file,
        }


class BaseExtractor(ABC):
    """Abstract base for all metadata type extractors."""

    def __init__(self, source_id: str) -> None:
        self.source_hash = hashlib.sha256(source_id.encode()).hexdigest()[:12]

    @abstractmethod
    def extract(self, file_path: Path) -> list[ExtractedPattern]:
        """Extract patterns from a single metadata file.

        Returns a list because one file can yield multiple patterns
        (e.g., a flow has decisions, lookups, updates, etc.).
        """

    def _parse_xml(self, file_path: Path) -> ET.Element | None:
        """Parse an XML file and return the root element, or None on error."""
        try:
            tree = ET.parse(file_path)
            return tree.getroot()
        except (ET.ParseError, OSError):
            return None

    def _compute_complexity(self, factors: dict[str, int]) -> int:
        """Compute a 1-5 complexity score from weighted factors.

        factors: dict of factor_name -> count
        """
        score = 0
        weights = {
            "decisions": 3,
            "loops": 3,
            "record_ops": 2,
            "screens": 2,
            "conditions": 1,
            "formulas": 2,
            "fields": 0.5,
            "elements": 0.3,
            "nesting_depth": 4,
            "subflows": 3,
        }
        for factor, count in factors.items():
            weight = weights.get(factor, 1)
            score += count * weight

        # Map to 1-5 scale
        if score <= 3:
            return 1
        elif score <= 8:
            return 2
        elif score <= 18:
            return 3
        elif score <= 35:
            return 4
        else:
            return 5

    def _detect_source_object(self, root: ET.Element) -> str:
        """Try to detect the primary Salesforce object from XML content."""
        # Check common locations for object references
        for tag in ("object", "objectType", "Object"):
            el = root.find(f".//{sf_tag(tag)}")
            if el is not None and el.text:
                return el.text.strip()

        # Check in record lookups/updates
        for parent_tag in ("recordLookups", "recordUpdates", "recordCreates"):
            for parent in find_all(root, parent_tag):
                obj = find_text(parent, "object")
                if obj:
                    return obj

        return "Unknown"

    def _extract_field_references(self, structure: dict) -> list[str]:
        """Recursively find field API name references in a structure dict."""
        fields: set[str] = set()
        self._walk_for_fields(structure, fields)
        return sorted(fields)

    def _walk_for_fields(self, obj: Any, fields: set[str]) -> None:
        """Walk a nested dict/list looking for field reference patterns."""
        if isinstance(obj, str):
            # Salesforce field patterns: Object.Field__c, Field__c, $Record.Field
            if "__c" in obj or "__r" in obj:
                # Extract just the field name
                parts = obj.split(".")
                for part in parts:
                    if "__c" in part or "__r" in part:
                        fields.add(part)
            # Standard field references
            if "." in obj and not obj.startswith("$"):
                parts = obj.split(".")
                if len(parts) == 2 and parts[1][0].isupper():
                    fields.add(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                self._walk_for_fields(v, fields)
        elif isinstance(obj, list):
            for item in obj:
                self._walk_for_fields(item, fields)

    def _auto_tags(self, pattern: ExtractedPattern) -> list[str]:
        """Generate automatic tags for a pattern."""
        tags = [
            pattern.pattern_type,
            pattern.category.lower().replace(" ", "-"),
        ]
        if pattern.source_object and pattern.source_object != "Unknown":
            tags.append(pattern.source_object.lower())
        if pattern.api_version:
            tags.append(f"api-v{pattern.api_version}")
        if pattern.complexity_score >= 4:
            tags.append("complex")
        if pattern.complexity_score <= 1:
            tags.append("simple")
        return tags
