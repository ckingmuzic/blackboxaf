"""Parser for Salesforce Page Layout metadata (.layout-meta.xml)."""

from __future__ import annotations

from pathlib import Path

from ..anonymizer import anonymize_structure
from ..base import BaseExtractor, ExtractedPattern, find_all, find_text


class LayoutExtractor(BaseExtractor):
    """Extract patterns from Salesforce Page Layout XML files."""

    def extract(self, file_path: Path) -> list[ExtractedPattern]:
        root = self._parse_xml(file_path)
        if root is None:
            return []

        ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""

        # Layout name from filename
        layout_name = file_path.stem.replace(".layout-meta", "")
        # Usually formatted as "Object-LayoutName"
        parts = layout_name.split("-", 1)
        source_object = parts[0] if len(parts) > 1 else "Unknown"
        display_name = parts[1] if len(parts) > 1 else layout_name

        # Parse layout sections
        sections = []
        field_refs = []
        for section in find_all(root, "layoutSections"):
            section_label = find_text(section, "label", "")
            style = find_text(section, "style", "")
            columns = find_all(section, "layoutColumns")

            section_fields = []
            for col in columns:
                for item in col.findall(f"{ns}layoutItems"):
                    behavior = find_text(item, "behavior", "")
                    field = find_text(item, "field", "")
                    if field:
                        section_fields.append({
                            "field": field,
                            "behavior": behavior,
                        })
                        field_refs.append(field)

            sections.append({
                "label": section_label,
                "style": style,
                "columnCount": len(columns),
                "fieldCount": len(section_fields),
                "fields": section_fields,
            })

        # Related lists
        related_lists = []
        for rl in find_all(root, "relatedLists"):
            related_lists.append({
                "relatedList": find_text(rl, "relatedList", ""),
                "fields": [
                    el.text for el in rl.findall(f"{ns}fields") if el.text
                ],
            })

        # Quick actions
        quick_actions = []
        for qa in find_all(root, "quickActionList"):
            for item in qa.findall(f"{ns}quickActionListItems"):
                quick_actions.append(find_text(item, "quickActionName", ""))

        structure = {
            "sectionCount": len(sections),
            "sections": sections,
            "relatedLists": related_lists,
            "quickActions": [q for q in quick_actions if q],
            "totalFields": len(field_refs),
        }

        factors = {
            "fields": len(field_refs),
            "elements": len(sections) + len(related_lists),
        }

        anonymized = anonymize_structure(structure)
        pattern = ExtractedPattern(
            pattern_type="layout_definition",
            category="Page Layout",
            name=f"Layout: {source_object} - {display_name.replace('_', ' ')}",
            description=f"Page layout for {source_object} with {len(sections)} sections and {len(field_refs)} fields.",
            source_object=source_object,
            structure=anonymized,
            field_references=sorted(set(field_refs)),
            api_version="",
            complexity_score=self._compute_complexity(factors),
            source_hash=self.source_hash,
            source_file=str(file_path.name),
        )
        pattern.tags = self._auto_tags(pattern)
        if related_lists:
            pattern.tags.append("has-related-lists")
        if quick_actions:
            pattern.tags.append("has-quick-actions")

        return [pattern]
