"""Parser for Salesforce Apex class metadata (.cls files).

Extracts structural patterns only - method signatures, annotations,
class hierarchy, SOQL patterns - NOT proprietary business logic.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..anonymizer import anonymize_structure
from ..base import BaseExtractor, ExtractedPattern


class ApexExtractor(BaseExtractor):
    """Extract structural patterns from Apex classes."""

    def extract(self, file_path: Path) -> list[ExtractedPattern]:
        if file_path.suffix != ".cls":
            return []

        content = self._read_file(file_path)
        if not content:
            return []

        class_name = file_path.stem
        analysis = self._analyze_apex(content, class_name)

        # Skip test classes and very small files for Phase 1
        if analysis.get("is_test") and not analysis.get("methods"):
            return []

        structure = {
            "className": class_name,
            "classType": analysis.get("class_type", "standard"),
            "accessModifier": analysis.get("access_modifier", "public"),
            "annotations": analysis.get("annotations", []),
            "interfaces": analysis.get("interfaces", []),
            "extends": analysis.get("extends", ""),
            "methods": analysis.get("methods", []),
            "soqlPatterns": analysis.get("soql_patterns", []),
            "dmlOperations": analysis.get("dml_operations", []),
            "objectsReferenced": analysis.get("objects_referenced", []),
            "isTest": analysis.get("is_test", False),
            "isBatch": analysis.get("is_batch", False),
            "isSchedulable": analysis.get("is_schedulable", False),
            "isTriggerHandler": analysis.get("is_trigger_handler", False),
            "isAuraEnabled": analysis.get("is_aura_enabled", False),
            "isRestResource": analysis.get("is_rest_resource", False),
        }

        # Field references from SOQL
        field_refs = analysis.get("objects_referenced", [])

        factors = {
            "elements": len(analysis.get("methods", [])),
            "conditions": len(analysis.get("soql_patterns", [])),
            "record_ops": len(analysis.get("dml_operations", [])),
        }

        # Detect primary object
        objects = analysis.get("objects_referenced", [])
        source_object = objects[0] if objects else "Unknown"

        anonymized = anonymize_structure(structure)
        pattern = ExtractedPattern(
            pattern_type="apex_class",
            category="Apex Logic",
            name=f"Apex: {class_name}",
            description=self._build_description(analysis),
            source_object=source_object,
            structure=anonymized,
            field_references=field_refs,
            api_version="",
            complexity_score=self._compute_complexity(factors),
            source_hash=self.source_hash,
            source_file=str(file_path.name),
        )
        pattern.tags = self._auto_tags(pattern)
        for ann in analysis.get("annotations", []):
            pattern.tags.append(f"annotation:{ann.lower()}")
        if analysis.get("is_batch"):
            pattern.tags.append("batch")
        if analysis.get("is_schedulable"):
            pattern.tags.append("schedulable")
        if analysis.get("is_rest_resource"):
            pattern.tags.append("rest-api")

        return [pattern]

    def _read_file(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def _analyze_apex(self, content: str, class_name: str) -> dict:
        analysis = {
            "class_type": "standard",
            "access_modifier": "public",
            "annotations": [],
            "interfaces": [],
            "extends": "",
            "methods": [],
            "soql_patterns": [],
            "dml_operations": [],
            "objects_referenced": [],
            "is_test": False,
            "is_batch": False,
            "is_schedulable": False,
            "is_trigger_handler": False,
            "is_aura_enabled": False,
            "is_rest_resource": False,
        }

        # Class-level annotations
        for match in re.finditer(r"@(\w+)(?:\([^)]*\))?", content):
            ann = match.group(1)
            if ann not in analysis["annotations"]:
                analysis["annotations"].append(ann)
            if ann == "isTest" or ann == "IsTest":
                analysis["is_test"] = True
            if ann == "AuraEnabled":
                analysis["is_aura_enabled"] = True
            if ann == "RestResource":
                analysis["is_rest_resource"] = True

        # Test class detection
        if "@isTest" in content.lower() or "testmethod" in content.lower():
            analysis["is_test"] = True

        # Class declaration
        class_match = re.search(
            r"(public|private|global)\s+"
            r"(?:(virtual|abstract|with sharing|without sharing|inherited sharing)\s+)*"
            r"class\s+\w+\s*"
            r"(?:extends\s+(\w+))?\s*"
            r"(?:implements\s+([\w\s,]+))?\s*\{",
            content,
        )
        if class_match:
            analysis["access_modifier"] = class_match.group(1)
            if class_match.group(3):
                analysis["extends"] = class_match.group(3)
            if class_match.group(4):
                interfaces = [i.strip() for i in class_match.group(4).split(",")]
                analysis["interfaces"] = interfaces
                if "Database.Batchable" in class_match.group(4):
                    analysis["is_batch"] = True
                if "Schedulable" in class_match.group(4):
                    analysis["is_schedulable"] = True

        # Method signatures (structural only, not the body)
        for match in re.finditer(
            r"(public|private|global|protected)\s+"
            r"(?:static\s+)?"
            r"(\w+(?:<[\w,\s]+>)?)\s+"
            r"(\w+)\s*\(([^)]*)\)",
            content,
        ):
            method = {
                "access": match.group(1),
                "returnType": match.group(2),
                "name": match.group(3),
                "paramCount": len([p for p in match.group(4).split(",") if p.strip()]),
            }
            analysis["methods"].append(method)

        # SOQL patterns (structure, not specific queries)
        for match in re.finditer(r"\[SELECT\s+(.+?)\s+FROM\s+(\w+)", content, re.IGNORECASE):
            obj = match.group(2)
            analysis["soql_patterns"].append({"object": obj})
            if obj not in analysis["objects_referenced"]:
                analysis["objects_referenced"].append(obj)

        # DML operations
        for op in ["insert", "update", "upsert", "delete", "undelete", "merge"]:
            if re.search(rf"\b{op}\s+\w+", content, re.IGNORECASE):
                if op not in analysis["dml_operations"]:
                    analysis["dml_operations"].append(op)

        # Trigger handler detection
        if "TriggerHandler" in content or "trigger" in class_name.lower():
            analysis["is_trigger_handler"] = True

        return analysis

    def _build_description(self, analysis: dict) -> str:
        parts = []
        if analysis["is_test"]:
            parts.append("Test class")
        elif analysis["is_batch"]:
            parts.append("Batch Apex class")
        elif analysis["is_schedulable"]:
            parts.append("Schedulable Apex class")
        elif analysis["is_rest_resource"]:
            parts.append("REST API resource class")
        elif analysis["is_trigger_handler"]:
            parts.append("Trigger handler class")
        else:
            parts.append(f"{analysis['access_modifier'].title()} Apex class")

        methods = analysis.get("methods", [])
        if methods:
            parts.append(f"with {len(methods)} methods")

        objects = analysis.get("objects_referenced", [])
        if objects:
            parts.append(f"operating on {', '.join(objects[:3])}")

        return " ".join(parts) + "."
