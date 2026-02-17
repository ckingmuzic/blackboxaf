"""Parser for Salesforce Validation Rule metadata (.validationRule-meta.xml)."""

from __future__ import annotations

from pathlib import Path

from ..anonymizer import anonymize_structure, extract_field_refs_from_formula
from ..base import BaseExtractor, ExtractedPattern, find_text


class ValidationRuleExtractor(BaseExtractor):
    """Extract patterns from Salesforce Validation Rule XML files."""

    def extract(self, file_path: Path) -> list[ExtractedPattern]:
        root = self._parse_xml(file_path)
        if root is None:
            return []

        full_name = find_text(root, "fullName", file_path.stem)
        active = find_text(root, "active", "false")
        description = find_text(root, "description", "")
        formula = find_text(root, "errorConditionFormula", "")
        error_msg = find_text(root, "errorMessage", "")
        error_field = find_text(root, "errorDisplayField", "")

        # Detect the parent object from the file path
        # Typical path: objects/Account/validationRules/MyRule.validationRule-meta.xml
        source_object = self._detect_object_from_path(file_path)

        # Extract field references from the formula
        field_refs = extract_field_refs_from_formula(formula)

        # Analyze formula structure
        formula_analysis = self._analyze_formula(formula)

        structure = {
            "active": active == "true",
            "formulaPattern": formula_analysis,
            "rawFormula": formula,
            "errorDisplayField": error_field,
            "fieldCount": len(field_refs),
        }

        # Complexity based on formula structure
        factors = {
            "conditions": formula_analysis.get("condition_count", 1),
            "nesting_depth": formula_analysis.get("nesting_depth", 0),
            "formulas": 1,
            "fields": len(field_refs),
        }

        anonymized = anonymize_structure(structure)
        pattern = ExtractedPattern(
            pattern_type="validation_rule",
            category="Data Validation",
            name=f"Validation: {self._genericize_name(full_name)}",
            description=self._build_description(formula_analysis, source_object, active),
            source_object=source_object,
            structure=anonymized,
            field_references=field_refs,
            api_version="",  # VRs don't have their own API version
            complexity_score=self._compute_complexity(factors),
            source_hash=self.source_hash,
            source_file=str(file_path.name),
        )
        pattern.tags = self._auto_tags(pattern)
        if active == "true":
            pattern.tags.append("active")
        for func in formula_analysis.get("functions_used", []):
            pattern.tags.append(f"func:{func.lower()}")

        return [pattern]

    def _detect_object_from_path(self, file_path: Path) -> str:
        """Detect the parent object from the validation rule file path."""
        parts = file_path.parts
        for i, part in enumerate(parts):
            if part == "objects" and i + 1 < len(parts):
                return parts[i + 1]
        return "Unknown"

    def _analyze_formula(self, formula: str) -> dict:
        """Analyze a validation rule formula for structural patterns."""
        if not formula:
            return {"functions_used": [], "condition_count": 0, "nesting_depth": 0}

        analysis = {
            "functions_used": [],
            "condition_count": 0,
            "nesting_depth": 0,
            "uses_permissions": False,
            "uses_record_type": False,
            "uses_profile": False,
            "operators": [],
        }

        # Detect formula functions
        sf_functions = [
            "AND", "OR", "NOT", "IF", "CASE", "ISBLANK", "ISNULL",
            "ISPICKVAL", "ISCHANGED", "ISNEW", "PRIORVALUE",
            "TEXT", "VALUE", "LEN", "LEFT", "RIGHT", "MID",
            "CONTAINS", "BEGINS", "INCLUDES",
            "TODAY", "NOW", "DATEVALUE", "DATETIMEVALUE",
            "YEAR", "MONTH", "DAY",
            "REGEX", "SUBSTITUTE", "TRIM",
            "NULLVALUE", "BLANKVALUE",
            "HYPERLINK", "IMAGE",
        ]
        formula_upper = formula.upper()
        for func in sf_functions:
            if func + "(" in formula_upper:
                analysis["functions_used"].append(func)

        # Count conditions (AND/OR branches)
        analysis["condition_count"] = (
            formula_upper.count("AND(") + formula_upper.count("OR(") + 1
        )

        # Nesting depth
        max_depth = 0
        current_depth = 0
        for char in formula:
            if char == "(":
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ")":
                current_depth -= 1
        analysis["nesting_depth"] = max_depth

        # Special references
        if "$Permission" in formula:
            analysis["uses_permissions"] = True
        if "$RecordType" in formula or "RecordType" in formula:
            analysis["uses_record_type"] = True
        if "$Profile" in formula or "$UserRole" in formula:
            analysis["uses_profile"] = True

        return analysis

    def _genericize_name(self, name: str) -> str:
        return name.replace("_", " ").strip()

    def _build_description(self, analysis: dict, obj: str, active: str) -> str:
        parts = []
        status = "Active" if active == "true" else "Inactive"
        parts.append(f"{status} validation rule")
        if obj != "Unknown":
            parts.append(f"on {obj}")

        funcs = analysis.get("functions_used", [])
        if funcs:
            parts.append(f"using {', '.join(funcs[:5])}")

        depth = analysis.get("nesting_depth", 0)
        if depth > 3:
            parts.append(f"(deeply nested: {depth} levels)")

        return " ".join(parts) + "."
