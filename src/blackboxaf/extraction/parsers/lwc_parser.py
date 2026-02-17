"""Parser for Salesforce Lightning Web Component metadata.

Extracts structural patterns from LWC bundles:
- Component structure from HTML templates
- Wire adapters and Apex calls from JS files
- API properties and event handlers
"""

from __future__ import annotations

import re
from pathlib import Path

from ..anonymizer import anonymize_structure
from ..base import BaseExtractor, ExtractedPattern


class LWCExtractor(BaseExtractor):
    """Extract patterns from Lightning Web Component bundles."""

    def extract(self, file_path: Path) -> list[ExtractedPattern]:
        """Extract from an LWC bundle directory or individual file.

        file_path should point to the component's .js file.
        We'll also look for adjacent .html and .js-meta.xml.
        """
        if file_path.suffix != ".js":
            return []

        # Skip test files
        if "__tests__" in str(file_path):
            return []

        component_name = file_path.stem
        bundle_dir = file_path.parent

        # Read the main JS file
        js_content = self._read_file(file_path)
        if not js_content:
            return []

        # Read HTML template if it exists
        html_path = bundle_dir / f"{component_name}.html"
        html_content = self._read_file(html_path)

        # Read meta XML if it exists
        meta_path = bundle_dir / f"{component_name}.js-meta.xml"
        meta_content = self._read_file(meta_path)

        # Analyze JS file
        js_analysis = self._analyze_js(js_content)

        # Analyze HTML template
        html_analysis = self._analyze_html(html_content) if html_content else {}

        # Analyze meta XML
        meta_analysis = self._analyze_meta(meta_content) if meta_content else {}

        structure = {
            "componentName": component_name,
            "js": js_analysis,
            "html": html_analysis,
            "meta": meta_analysis,
        }

        # Compute complexity
        factors = {
            "fields": len(js_analysis.get("api_properties", [])),
            "elements": (
                len(js_analysis.get("wire_adapters", []))
                + len(js_analysis.get("apex_calls", []))
                + len(html_analysis.get("child_components", []))
            ),
            "conditions": len(html_analysis.get("conditionals", [])),
            "loops": len(html_analysis.get("iterations", [])),
        }

        anonymized = anonymize_structure(structure)
        pattern = ExtractedPattern(
            pattern_type="lwc_component",
            category="UI Component",
            name=f"LWC: {self._format_component_name(component_name)}",
            description=self._build_description(js_analysis, html_analysis, meta_analysis),
            source_object=meta_analysis.get("primaryObject", "Unknown"),
            structure=anonymized,
            field_references=js_analysis.get("field_references", []),
            api_version=meta_analysis.get("apiVersion", ""),
            complexity_score=self._compute_complexity(factors),
            source_hash=self.source_hash,
            source_file=str(file_path.name),
        )
        pattern.tags = self._auto_tags(pattern)
        if js_analysis.get("wire_adapters"):
            pattern.tags.append("uses-wire")
        if js_analysis.get("apex_calls"):
            pattern.tags.append("calls-apex")
        if js_analysis.get("navigation"):
            pattern.tags.append("uses-navigation")
        for target in meta_analysis.get("targets", []):
            pattern.tags.append(f"target:{target}")

        return [pattern]

    def _read_file(self, path: Path) -> str:
        """Read a file's content, return empty string on failure."""
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def _analyze_js(self, content: str) -> dict:
        """Analyze a LWC JavaScript file for structural patterns."""
        analysis = {
            "api_properties": [],
            "tracked_properties": [],
            "wire_adapters": [],
            "apex_calls": [],
            "event_handlers": [],
            "navigation": False,
            "toast": False,
            "lifecycle_hooks": [],
            "field_references": [],
        }

        # @api properties
        for match in re.finditer(r"@api\s+(\w+)", content):
            analysis["api_properties"].append(match.group(1))

        # @track properties (deprecated but still common)
        for match in re.finditer(r"@track\s+(\w+)", content):
            analysis["tracked_properties"].append(match.group(1))

        # @wire decorators
        for match in re.finditer(r"@wire\((\w+)(?:,\s*\{([^}]*)\})?\)", content):
            adapter = match.group(1)
            analysis["wire_adapters"].append(adapter)

        # Apex imports
        for match in re.finditer(r"import\s+(\w+)\s+from\s+['\"]@salesforce/apex/(\w+\.\w+)['\"]", content):
            analysis["apex_calls"].append({
                "localName": match.group(1),
                "method": match.group(2),
            })

        # Schema field imports
        for match in re.finditer(r"import\s+\w+\s+from\s+['\"]@salesforce/schema/(\w+\.\w+)['\"]", content):
            analysis["field_references"].append(match.group(1))

        # Event handlers
        for match in re.finditer(r"handle\w+\s*\(", content):
            analysis["event_handlers"].append(match.group(0).rstrip("(").strip())

        # Navigation
        if "NavigationMixin" in content or "this[NavigationMixin.Navigate]" in content:
            analysis["navigation"] = True

        # Toast messages
        if "ShowToastEvent" in content:
            analysis["toast"] = True

        # Lifecycle hooks
        for hook in ["connectedCallback", "disconnectedCallback", "renderedCallback", "errorCallback"]:
            if hook in content:
                analysis["lifecycle_hooks"].append(hook)

        return analysis

    def _analyze_html(self, content: str) -> dict:
        """Analyze a LWC HTML template for structural patterns."""
        analysis = {
            "child_components": [],
            "conditionals": [],
            "iterations": [],
            "slots": False,
            "forms": False,
        }

        # Custom child components (c-xxx or lightning-xxx)
        for match in re.finditer(r"<(c-\w+|lightning-\w+)", content):
            comp = match.group(1)
            if comp not in analysis["child_components"]:
                analysis["child_components"].append(comp)

        # Conditionals
        analysis["conditionals"] = [
            m.group(1) for m in re.finditer(r"(?:if:true|if:false|lwc:if|lwc:elseif)=\{([^}]+)\}", content)
        ]

        # Iterations
        analysis["iterations"] = [
            m.group(1) for m in re.finditer(r"for:each=\{([^}]+)\}", content)
        ]

        # Slots
        if "<slot" in content:
            analysis["slots"] = True

        # Form elements
        if "lightning-input" in content or "lightning-combobox" in content:
            analysis["forms"] = True

        return analysis

    def _analyze_meta(self, content: str) -> dict:
        """Analyze a .js-meta.xml file."""
        analysis = {
            "apiVersion": "",
            "isExposed": False,
            "targets": [],
            "primaryObject": "Unknown",
        }

        # API version
        match = re.search(r"<apiVersion>([\d.]+)</apiVersion>", content)
        if match:
            analysis["apiVersion"] = match.group(1)

        # Exposed
        if "<isExposed>true</isExposed>" in content:
            analysis["isExposed"] = True

        # Targets
        for match in re.finditer(r"<target>([\w:]+)</target>", content):
            target = match.group(1).split("__")[-1]
            analysis["targets"].append(target)

        # Object binding
        match = re.search(r"<objects>\s*<object>(\w+)</object>", content)
        if match:
            analysis["primaryObject"] = match.group(1)

        return analysis

    def _format_component_name(self, name: str) -> str:
        """Convert camelCase component name to readable form."""
        return re.sub(r"([A-Z])", r" \1", name).strip().title()

    def _build_description(self, js: dict, html: dict, meta: dict) -> str:
        parts = ["Lightning Web Component"]
        if meta.get("targets"):
            parts.append(f"for {', '.join(meta['targets'][:3])}")
        features = []
        if js.get("wire_adapters"):
            features.append(f"{len(js['wire_adapters'])} wire adapters")
        if js.get("apex_calls"):
            features.append(f"{len(js['apex_calls'])} Apex calls")
        if js.get("api_properties"):
            features.append(f"{len(js['api_properties'])} @api props")
        if html.get("child_components"):
            features.append(f"{len(html['child_components'])} child components")
        if features:
            parts.append(f"with {', '.join(features)}")
        return " ".join(parts) + "."
