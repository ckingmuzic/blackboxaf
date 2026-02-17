"""Parser for Salesforce Flow metadata (.flow-meta.xml).

Extracts both a full-flow pattern and individual element patterns
(decisions, record lookups, record updates, screens, assignments, etc.).
"""

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

# Flow element tags we extract as individual patterns
_ELEMENT_TAGS = [
    "decisions",
    "recordLookups",
    "recordUpdates",
    "recordCreates",
    "recordDeletes",
    "screens",
    "assignments",
    "loops",
    "actionCalls",
    "subflows",
    "formulas",
    "collectionProcessors",
]

# Map XML tags to pattern types
_TAG_TO_TYPE = {
    "decisions": "flow_decision",
    "recordLookups": "flow_record_lookup",
    "recordUpdates": "flow_record_update",
    "recordCreates": "flow_record_create",
    "recordDeletes": "flow_record_delete",
    "screens": "flow_screen",
    "assignments": "flow_assignment",
    "loops": "flow_loop",
    "actionCalls": "flow_action_call",
    "subflows": "flow_subflow",
    "formulas": "flow_formula",
    "collectionProcessors": "flow_collection_processor",
}


class FlowExtractor(BaseExtractor):
    """Extract patterns from Salesforce Flow XML files."""

    def extract(self, file_path: Path) -> list[ExtractedPattern]:
        root = self._parse_xml(file_path)
        if root is None:
            return []

        patterns: list[ExtractedPattern] = []
        api_version = find_text(root, "apiVersion", "unknown")
        process_type = find_text(root, "processType", "unknown")
        flow_status = find_text(root, "status", "unknown")
        flow_label = find_text(root, "label", file_path.stem)
        trigger_type = find_text(root, "recordTriggerType", "")
        run_mode = find_text(root, "runInMode", "")

        # Detect primary object from the flow
        source_object = self._detect_flow_object(root)

        # Count elements for complexity scoring
        element_counts = {}
        for tag in _ELEMENT_TAGS:
            elements = find_all(root, tag)
            if elements:
                element_counts[tag] = len(elements)

        # --- Full flow pattern ---
        flow_structure = {
            "processType": process_type,
            "status": flow_status,
            "triggerType": trigger_type,
            "runInMode": run_mode,
            "elements": {},
            "variables": [],
            "topology": [],
        }

        # Capture variable signatures (input/output interface)
        for var_el in find_all(root, "variables"):
            var_info = {
                "name": find_text(var_el, "name"),
                "dataType": find_text(var_el, "dataType"),
                "isInput": find_text(var_el, "isInput") == "true",
                "isOutput": find_text(var_el, "isOutput") == "true",
                "isCollection": find_text(var_el, "isCollection") == "true",
            }
            apex_class = find_text(var_el, "apexClass")
            if apex_class:
                var_info["apexClass"] = apex_class
            flow_structure["variables"].append(var_info)

        # Capture element counts
        for tag, count in element_counts.items():
            flow_structure["elements"][tag] = count

        # Build topology (what connects to what)
        flow_structure["topology"] = self._build_topology(root)

        # Compute complexity for full flow
        complexity_factors = {
            "decisions": element_counts.get("decisions", 0),
            "loops": element_counts.get("loops", 0),
            "record_ops": (
                element_counts.get("recordLookups", 0)
                + element_counts.get("recordUpdates", 0)
                + element_counts.get("recordCreates", 0)
                + element_counts.get("recordDeletes", 0)
            ),
            "screens": element_counts.get("screens", 0),
            "formulas": element_counts.get("formulas", 0),
            "subflows": element_counts.get("subflows", 0),
            "elements": sum(element_counts.values()),
        }

        full_structure = anonymize_structure(flow_structure)
        full_pattern = ExtractedPattern(
            pattern_type="flow_full",
            category="Flow Logic",
            name=f"Flow: {self._genericize_name(flow_label)}",
            description=self._describe_flow(process_type, trigger_type, element_counts, source_object),
            source_object=source_object,
            structure=full_structure,
            field_references=self._extract_field_references(full_structure),
            api_version=api_version,
            complexity_score=self._compute_complexity(complexity_factors),
            source_hash=self.source_hash,
            source_file=str(file_path.name),
        )
        full_pattern.tags = self._auto_tags(full_pattern)
        full_pattern.tags.append(process_type.lower())
        if trigger_type:
            full_pattern.tags.append(trigger_type.lower())
        patterns.append(full_pattern)

        # --- Individual element patterns ---
        for tag in _ELEMENT_TAGS:
            for element in find_all(root, tag):
                pattern = self._extract_element_pattern(
                    element, tag, api_version, source_object, file_path
                )
                if pattern:
                    patterns.append(pattern)

        return patterns

    def _extract_element_pattern(
        self,
        element,
        tag: str,
        api_version: str,
        source_object: str,
        file_path: Path,
    ) -> ExtractedPattern | None:
        """Extract a single flow element as a pattern."""
        name = find_text(element, "name", "unnamed")
        label = find_text(element, "label", name)
        pattern_type = _TAG_TO_TYPE.get(tag, f"flow_{tag}")

        # Build element structure
        raw_structure = element_to_dict(element)
        # Unwrap the outer tag
        structure = raw_structure.get(tag, raw_structure)

        # Remove layout coordinates (not transferable)
        structure.pop("locationX", None)
        structure.pop("locationY", None)

        # Element-specific complexity
        factors = self._element_complexity_factors(element, tag)

        # Detect object for record operations
        el_object = find_text(element, "object") or source_object

        anonymized = anonymize_structure(structure)
        pattern = ExtractedPattern(
            pattern_type=pattern_type,
            category="Flow Logic",
            name=f"{tag.rstrip('s').title()}: {self._genericize_name(label)}",
            description=self._describe_element(tag, label, el_object),
            source_object=el_object,
            structure=anonymized,
            field_references=self._extract_field_references(anonymized),
            api_version=api_version,
            complexity_score=self._compute_complexity(factors),
            source_hash=self.source_hash,
            source_file=str(file_path.name),
        )
        pattern.tags = self._auto_tags(pattern)
        return pattern

    def _detect_flow_object(self, root) -> str:
        """Detect the primary object a flow operates on."""
        # Check start element for record-triggered flows
        start = root.find(f".//{{{root.tag.split('}')[0][1:]}}}start")
        if start is not None:
            obj = find_text(start, "object")
            if obj:
                return obj

        # Check record operations for the most common object
        objects: dict[str, int] = {}
        for tag in ("recordLookups", "recordUpdates", "recordCreates", "recordDeletes"):
            for el in find_all(root, tag):
                obj = find_text(el, "object")
                if obj:
                    objects[obj] = objects.get(obj, 0) + 1

        if objects:
            return max(objects, key=objects.get)

        return self._detect_source_object(root)

    def _build_topology(self, root) -> list[dict]:
        """Build a connection topology showing how elements connect."""
        connections = []
        ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""

        for tag in _ELEMENT_TAGS:
            for element in find_all(root, tag):
                name = find_text(element, "name")
                if not name:
                    continue

                # Standard connector
                connector = element.find(f"{ns}connector")
                if connector is not None:
                    target = connector.find(f"{ns}targetReference")
                    if target is not None and target.text:
                        connections.append({
                            "from": name,
                            "to": target.text,
                            "type": "next",
                        })

                # Fault connector
                fault = element.find(f"{ns}faultConnector")
                if fault is not None:
                    target = fault.find(f"{ns}targetReference")
                    if target is not None and target.text:
                        connections.append({
                            "from": name,
                            "to": target.text,
                            "type": "fault",
                        })

                # Decision rules have connectors
                for rule in element.findall(f"{ns}rules"):
                    rule_connector = rule.find(f"{ns}connector")
                    if rule_connector is not None:
                        target = rule_connector.find(f"{ns}targetReference")
                        if target is not None and target.text:
                            rule_name = rule.find(f"{ns}name")
                            connections.append({
                                "from": name,
                                "to": target.text,
                                "type": f"rule:{rule_name.text if rule_name is not None else 'unnamed'}",
                            })

                # Default connector for decisions
                default_conn = element.find(f"{ns}defaultConnector")
                if default_conn is not None:
                    target = default_conn.find(f"{ns}targetReference")
                    if target is not None and target.text:
                        connections.append({
                            "from": name,
                            "to": target.text,
                            "type": "default",
                        })

                # Next-value connector for loops
                next_val = element.find(f"{ns}nextValueConnector")
                if next_val is not None:
                    target = next_val.find(f"{ns}targetReference")
                    if target is not None and target.text:
                        connections.append({
                            "from": name,
                            "to": target.text,
                            "type": "loop_next",
                        })

                # No-more-values connector for loops
                no_more = element.find(f"{ns}noMoreValuesConnector")
                if no_more is not None:
                    target = no_more.find(f"{ns}targetReference")
                    if target is not None and target.text:
                        connections.append({
                            "from": name,
                            "to": target.text,
                            "type": "loop_done",
                        })

        return connections

    def _element_complexity_factors(self, element, tag: str) -> dict[str, int]:
        """Compute complexity factors for an individual flow element."""
        ns = element.tag.split("}")[0] + "}" if "}" in element.tag else ""
        factors: dict[str, int] = {"elements": 1}

        if tag == "decisions":
            rules = element.findall(f"{ns}rules")
            factors["decisions"] = 1
            total_conditions = 0
            for rule in rules:
                total_conditions += len(rule.findall(f"{ns}conditions"))
            factors["conditions"] = total_conditions

        elif tag == "screens":
            fields = element.findall(f"{ns}fields")
            factors["screens"] = 1
            factors["fields"] = len(fields)

        elif tag in ("recordLookups", "recordUpdates", "recordCreates", "recordDeletes"):
            factors["record_ops"] = 1
            filters = element.findall(f"{ns}filters")
            factors["conditions"] = len(filters)
            inputs = element.findall(f"{ns}inputAssignments")
            factors["fields"] = len(inputs)

        elif tag == "loops":
            factors["loops"] = 1

        elif tag == "actionCalls":
            inputs = element.findall(f"{ns}inputParameters")
            outputs = element.findall(f"{ns}outputParameters")
            factors["fields"] = len(inputs) + len(outputs)

        return factors

    def _genericize_name(self, name: str) -> str:
        """Make a flow element name more generic for the pattern catalog."""
        # Keep the structural intent, remove org-specific prefixes
        name = name.replace("_", " ").strip()
        return name

    def _describe_flow(
        self, process_type: str, trigger_type: str,
        element_counts: dict, source_object: str,
    ) -> str:
        """Generate a human-readable description of a flow pattern."""
        parts = [f"{process_type} flow"]
        if trigger_type:
            parts[0] = f"{trigger_type}-triggered {parts[0]}"
        if source_object != "Unknown":
            parts.append(f"on {source_object}")

        element_summary = []
        for tag, count in sorted(element_counts.items()):
            element_summary.append(f"{count} {tag}")
        if element_summary:
            parts.append(f"with {', '.join(element_summary)}")

        return ". ".join(parts) + "."

    def _describe_element(self, tag: str, label: str, obj: str) -> str:
        """Generate a description for an individual flow element."""
        readable_tag = tag.replace("record", "Record ").replace("Lookups", "Lookup")
        readable_tag = readable_tag.replace("Updates", "Update").replace("Creates", "Create")
        readable_tag = readable_tag.replace("Deletes", "Delete").replace("actionCalls", "Action Call")
        if obj and obj != "Unknown":
            return f"{readable_tag} on {obj}: {label}"
        return f"{readable_tag}: {label}"
