"""Parser for Salesforce Custom Object and Field metadata."""

from __future__ import annotations

from pathlib import Path

from ..anonymizer import anonymize_structure
from ..base import (
    BaseExtractor,
    ExtractedPattern,
    element_to_dict,
    find_all,
    find_text,
)


class ObjectExtractor(BaseExtractor):
    """Extract patterns from Salesforce Object/Field XML files."""

    def extract(self, file_path: Path) -> list[ExtractedPattern]:
        root = self._parse_xml(file_path)
        if root is None:
            return []

        file_name = file_path.name

        if file_name.endswith(".object-meta.xml"):
            return self._extract_object(root, file_path)
        elif file_name.endswith(".field-meta.xml"):
            return self._extract_field(root, file_path)
        else:
            return []

    def _extract_object(self, root, file_path: Path) -> list[ExtractedPattern]:
        """Extract pattern from a custom object definition."""
        obj_name = file_path.stem.replace(".object-meta", "")

        # Gather object-level configuration
        structure = {
            "objectName": obj_name,
            "sharingModel": find_text(root, "sharingModel", ""),
            "deploymentStatus": find_text(root, "deploymentStatus", ""),
            "enableActivities": find_text(root, "enableActivities", ""),
            "enableHistory": find_text(root, "enableHistory", ""),
            "enableReports": find_text(root, "enableReports", ""),
            "enableSearch": find_text(root, "enableSearch", ""),
            "nameFieldType": "",
            "actionOverrides": [],
        }

        # Name field info
        name_field = root.find(f".//{{{root.tag.split('}')[0][1:]}}}nameField")
        if name_field is not None:
            structure["nameFieldType"] = find_text(name_field, "type", "")

        # Action overrides summary (not the details)
        overrides = find_all(root, "actionOverrides")
        override_types = set()
        for ov in overrides:
            action = find_text(ov, "actionName")
            ov_type = find_text(ov, "type")
            if action and ov_type != "Default":
                override_types.add(f"{action}:{ov_type}")
        structure["actionOverrides"] = sorted(override_types)

        factors = {
            "elements": len(override_types) + 1,
        }

        anonymized = anonymize_structure(structure)
        pattern = ExtractedPattern(
            pattern_type="object_definition",
            category="Data Model",
            name=f"Object: {obj_name}",
            description=f"Custom object definition for {obj_name}.",
            source_object=obj_name,
            structure=anonymized,
            field_references=[obj_name],
            api_version="",
            complexity_score=self._compute_complexity(factors),
            source_hash=self.source_hash,
            source_file=str(file_path.name),
        )
        pattern.tags = self._auto_tags(pattern)
        return [pattern]

    def _extract_field(self, root, file_path: Path) -> list[ExtractedPattern]:
        """Extract pattern from a custom field definition."""
        full_name = find_text(root, "fullName", file_path.stem.replace(".field-meta", ""))
        field_type = find_text(root, "type", "Unknown")
        label = find_text(root, "label", full_name)
        required = find_text(root, "required", "false")
        unique = find_text(root, "unique", "false")
        external_id = find_text(root, "externalId", "false")
        length = find_text(root, "length", "")
        precision = find_text(root, "precision", "")
        scale = find_text(root, "scale", "")
        default_value = find_text(root, "defaultValue", "")
        formula = find_text(root, "formula", "")
        reference_to = find_text(root, "referenceTo", "")
        relationship_name = find_text(root, "relationshipName", "")
        delete_constraint = find_text(root, "deleteConstraint", "")

        # Detect parent object from path
        source_object = self._detect_object_from_path(file_path)

        structure = {
            "fieldName": full_name,
            "type": field_type,
            "required": required == "true",
            "unique": unique == "true",
            "externalId": external_id == "true",
        }

        if length:
            structure["length"] = length
        if precision:
            structure["precision"] = precision
        if scale:
            structure["scale"] = scale
        if default_value:
            structure["hasDefaultValue"] = True
        if formula:
            structure["isFormula"] = True
            structure["formulaReturnType"] = find_text(root, "formulaTreatBlanksAs", "")
        if reference_to:
            structure["referenceTo"] = reference_to
            structure["relationshipName"] = relationship_name
            structure["deleteConstraint"] = delete_constraint

        # Picklist values (just the structure, not specific values)
        value_set = root.find(f".//{{{root.tag.split('}')[0][1:]}}}valueSet")
        if value_set is not None:
            structure["hasPicklist"] = True
            restricted = find_text(value_set, "restricted", "false")
            structure["picklistRestricted"] = restricted == "true"

        factors = {
            "fields": 1,
            "formulas": 1 if formula else 0,
        }

        field_refs = [f"{source_object}.{full_name}"] if source_object != "Unknown" else [full_name]
        if reference_to:
            field_refs.append(reference_to)

        anonymized = anonymize_structure(structure)
        pattern = ExtractedPattern(
            pattern_type="field_definition",
            category="Data Model",
            name=f"Field: {source_object}.{full_name}" if source_object != "Unknown" else f"Field: {full_name}",
            description=self._build_description(full_name, field_type, source_object, reference_to),
            source_object=source_object,
            structure=anonymized,
            field_references=field_refs,
            api_version="",
            complexity_score=self._compute_complexity(factors),
            source_hash=self.source_hash,
            source_file=str(file_path.name),
        )
        pattern.tags = self._auto_tags(pattern)
        pattern.tags.append(f"type:{field_type.lower()}")
        if formula:
            pattern.tags.append("formula-field")
        if reference_to:
            pattern.tags.append("lookup")
        return [pattern]

    def _detect_object_from_path(self, file_path: Path) -> str:
        parts = file_path.parts
        for i, part in enumerate(parts):
            if part == "objects" and i + 1 < len(parts):
                return parts[i + 1]
        return "Unknown"

    def _build_description(self, name: str, ftype: str, obj: str, ref_to: str) -> str:
        parts = [f"{ftype} field"]
        if obj != "Unknown":
            parts.append(f"on {obj}")
        if ref_to:
            parts.append(f"(lookup to {ref_to})")
        return " ".join(parts) + "."
