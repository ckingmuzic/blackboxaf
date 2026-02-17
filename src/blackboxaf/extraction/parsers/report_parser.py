"""Parser for Salesforce Report metadata (.report-meta.xml)."""

from __future__ import annotations

from pathlib import Path

from ..anonymizer import anonymize_structure
from ..base import BaseExtractor, ExtractedPattern, find_all, find_text


class ReportExtractor(BaseExtractor):
    """Extract patterns from Salesforce Report XML files."""

    def extract(self, file_path: Path) -> list[ExtractedPattern]:
        root = self._parse_xml(file_path)
        if root is None:
            return []

        name = find_text(root, "name", file_path.stem)
        report_type = find_text(root, "reportType", "Unknown")
        format_type = find_text(root, "format", "Tabular")
        api_version = find_text(root, "apiVersion", "")

        # Columns
        columns = []
        for col in find_all(root, "columns"):
            col_field = find_text(col, "field", "")
            col_agg = find_text(col, "aggregateTypes", "")
            if col_field:
                columns.append({"field": col_field, "aggregate": col_agg})

        # Filters
        filters = []
        for flt in find_all(root, "filter"):
            criteria_items = find_all(flt, "criteriaItems")
            for ci in criteria_items:
                filters.append({
                    "column": find_text(ci, "column", ""),
                    "operator": find_text(ci, "operator", ""),
                    "snapshot": find_text(ci, "snapshot", ""),
                })
            bool_filter = find_text(flt, "booleanFilter", "")
            if bool_filter:
                filters.append({"booleanFilter": bool_filter})

        # Groupings
        groupings = []
        for grp in find_all(root, "groupingsDown"):
            groupings.append({
                "field": find_text(grp, "field", ""),
                "dateGranularity": find_text(grp, "dateGranularity", ""),
                "sortOrder": find_text(grp, "sortOrder", ""),
            })
        for grp in find_all(root, "groupingsAcross"):
            groupings.append({
                "field": find_text(grp, "field", ""),
                "dateGranularity": find_text(grp, "dateGranularity", ""),
                "sortOrder": find_text(grp, "sortOrder", ""),
                "direction": "across",
            })

        # Custom summary formulas
        formulas = []
        for csf in find_all(root, "customDetailFormulas") + find_all(root, "customSummaryFormulas"):
            formulas.append({
                "label": find_text(csf, "label", ""),
                "formulaType": find_text(csf, "formulaType", ""),
                "formula": find_text(csf, "formula", ""),
            })

        # Chart info
        chart = root.find(f".//{{{root.tag.split('}')[0][1:]}}}chart") if root.tag and "}" in root.tag else None
        chart_info = {}
        if chart is not None:
            chart_info = {
                "chartType": find_text(chart, "chartType", ""),
                "enableHoverLabels": find_text(chart, "enableHoverLabels", ""),
                "legendPosition": find_text(chart, "legendPosition", ""),
            }

        # Field references
        field_refs = [c["field"] for c in columns if c["field"]]
        field_refs += [g["field"] for g in groupings if g["field"]]
        field_refs += [f["column"] for f in filters if f.get("column")]

        structure = {
            "reportType": report_type,
            "format": format_type,
            "columnCount": len(columns),
            "columns": columns,
            "filterCount": len(filters),
            "filters": filters,
            "groupings": groupings,
            "customFormulas": formulas,
            "chart": chart_info,
        }

        factors = {
            "fields": len(columns),
            "conditions": len(filters),
            "formulas": len(formulas),
            "elements": len(groupings) + (1 if chart_info else 0),
        }

        anonymized = anonymize_structure(structure)
        pattern = ExtractedPattern(
            pattern_type="report_definition",
            category="Reporting",
            name=f"Report: {name.replace('_', ' ')}",
            description=self._build_description(format_type, report_type, columns, groupings, formulas),
            source_object=report_type,
            structure=anonymized,
            field_references=sorted(set(field_refs)),
            api_version=api_version,
            complexity_score=self._compute_complexity(factors),
            source_hash=self.source_hash,
            source_file=str(file_path.name),
        )
        pattern.tags = self._auto_tags(pattern)
        pattern.tags.append(f"format:{format_type.lower()}")
        if chart_info:
            pattern.tags.append("has-chart")
        if formulas:
            pattern.tags.append("custom-formulas")

        return [pattern]

    def _build_description(self, fmt, rtype, columns, groupings, formulas):
        parts = [f"{fmt} report on {rtype}"]
        parts.append(f"with {len(columns)} columns")
        if groupings:
            parts.append(f"{len(groupings)} groupings")
        if formulas:
            parts.append(f"{len(formulas)} custom formulas")
        return ", ".join(parts) + "."
