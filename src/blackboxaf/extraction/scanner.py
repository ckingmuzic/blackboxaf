"""Scanner that walks SFDX project directories and dispatches to parsers."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .anonymizer import anonymize_field_name, configure_scrubber, get_scrubber
from .base import ExtractedPattern
from .parsers.apex_parser import ApexExtractor
from .parsers.flow_parser import FlowExtractor
from .parsers.layout_parser import LayoutExtractor
from .parsers.lwc_parser import LWCExtractor
from .parsers.object_parser import ObjectExtractor
from .parsers.report_parser import ReportExtractor
from .parsers.validation_parser import ValidationRuleExtractor

logger = logging.getLogger(__name__)


@dataclass
class ScanProgress:
    """Tracks scanning progress for UI updates."""

    total_files: int = 0
    processed_files: int = 0
    patterns_found: int = 0
    current_file: str = ""
    errors: list[str] = field(default_factory=list)
    metadata_counts: dict[str, int] = field(default_factory=dict)

    @property
    def percent(self) -> float:
        if self.total_files == 0:
            return 0
        return (self.processed_files / self.total_files) * 100


@dataclass
class ScanResult:
    """Result of scanning an SFDX project."""

    source_id: str
    source_hash: str
    project_path: str
    patterns: list[ExtractedPattern]
    progress: ScanProgress


# Map file patterns to their extractor classes
_FILE_PATTERNS = {
    ".flow-meta.xml": "flow",
    ".validationRule-meta.xml": "validation",
    ".object-meta.xml": "object",
    ".field-meta.xml": "field",
    ".report-meta.xml": "report",
    ".layout-meta.xml": "layout",
}


def _classify_file(file_path: Path) -> str | None:
    """Determine what kind of metadata file this is."""
    name = file_path.name

    for suffix, file_type in _FILE_PATTERNS.items():
        if name.endswith(suffix):
            return file_type

    # LWC: .js files inside lwc/ directories
    if file_path.suffix == ".js" and "lwc" in file_path.parts:
        # Only the main component JS file, not helpers
        parent_name = file_path.parent.name
        if file_path.stem == parent_name:
            return "lwc"

    # Apex classes
    if file_path.suffix == ".cls" and "classes" in file_path.parts:
        return "apex"

    return None


def scan_sfdx_project(
    project_path: str | Path,
    progress_callback: Callable[[ScanProgress], None] | None = None,
    custom_brand_terms: list[str] | None = None,
) -> ScanResult:
    """Scan an SFDX project directory and extract all patterns.

    Args:
        project_path: Path to the SFDX project root (containing sfdx-project.json
                      or force-app directory)
        progress_callback: Optional callback for real-time progress updates

    Returns:
        ScanResult with all extracted patterns
    """
    project_path = Path(project_path)
    source_id = project_path.name
    source_hash = hashlib.sha256(source_id.encode()).hexdigest()[:12]

    progress = ScanProgress()

    # Find the force-app directory
    force_app = _find_force_app(project_path)
    if force_app is None:
        progress.errors.append(f"No force-app directory found in {project_path}")
        return ScanResult(
            source_id=source_id,
            source_hash=source_hash,
            project_path=str(project_path),
            patterns=[],
            progress=progress,
        )

    # Discover all metadata files
    all_files = _discover_files(force_app)
    progress.total_files = len(all_files)

    if progress_callback:
        progress_callback(progress)

    # ── Brand detection phase ──
    # Collect all custom field names for auto-detection
    field_names = []
    for file_path, file_type in all_files:
        if file_type == "field":
            # Extract field name from path: objects/Obj/fields/FieldName.field-meta.xml
            field_stem = file_path.stem.replace(".field-meta", "")
            parts = file_path.parts
            for i, part in enumerate(parts):
                if part == "objects" and i + 1 < len(parts):
                    field_names.append(f"{parts[i + 1]}.{field_stem}")
                    break
            else:
                field_names.append(field_stem)

    scrubber = configure_scrubber(
        org_name=source_id,
        custom_terms=custom_brand_terms,
        field_names=field_names,
    )
    detected = list(scrubber.brand_map.keys()) if scrubber else []
    if detected:
        logger.info(f"Auto-detected {len(detected)} brand terms to scrub: {detected[:10]}")

    # Initialize extractors
    extractors = {
        "flow": FlowExtractor(source_id),
        "validation": ValidationRuleExtractor(source_id),
        "object": ObjectExtractor(source_id),
        "field": ObjectExtractor(source_id),
        "report": ReportExtractor(source_id),
        "layout": LayoutExtractor(source_id),
        "lwc": LWCExtractor(source_id),
        "apex": ApexExtractor(source_id),
    }

    all_patterns: list[ExtractedPattern] = []

    for file_path, file_type in all_files:
        progress.current_file = str(file_path.relative_to(project_path))
        progress.processed_files += 1

        # Track metadata type counts
        progress.metadata_counts[file_type] = (
            progress.metadata_counts.get(file_type, 0) + 1
        )

        extractor = extractors.get(file_type)
        if extractor is None:
            continue

        try:
            patterns = extractor.extract(file_path)
            all_patterns.extend(patterns)
            progress.patterns_found += len(patterns)
        except Exception as e:
            error_msg = f"Error parsing {file_path.name}: {e}"
            progress.errors.append(error_msg)
            logger.warning(error_msg)

        if progress_callback and progress.processed_files % 50 == 0:
            progress_callback(progress)

    # ── Post-processing: scrub brand terms from names and field refs ──
    scrubber = get_scrubber()
    if scrubber:
        for p in all_patterns:
            p.name = scrubber.scrub(p.name)
            p.description = scrubber.scrub(p.description)
            p.source_object = scrubber.scrub(p.source_object)
            p.field_references = [scrubber.scrub(f) for f in p.field_references]
            p.tags = [scrubber.scrub(t) for t in p.tags]

    # Final callback
    if progress_callback:
        progress_callback(progress)

    return ScanResult(
        source_id=source_id,
        source_hash=source_hash,
        project_path=str(project_path),
        patterns=all_patterns,
        progress=progress,
    )


def _find_force_app(project_path: Path) -> Path | None:
    """Find the force-app directory in an SFDX project."""
    # Direct force-app child
    direct = project_path / "force-app"
    if direct.is_dir():
        return direct

    # Check if the path itself is a force-app
    if project_path.name == "force-app":
        return project_path

    # Check sfdx-project.json for package directories
    sfdx_config = project_path / "sfdx-project.json"
    if sfdx_config.exists():
        try:
            import json
            config = json.loads(sfdx_config.read_text())
            for pkg in config.get("packageDirectories", []):
                pkg_path = project_path / pkg.get("path", "")
                if pkg_path.is_dir():
                    return pkg_path
        except (json.JSONDecodeError, OSError):
            pass

    return None


def _discover_files(force_app: Path) -> list[tuple[Path, str]]:
    """Discover all parseable metadata files under force-app."""
    files: list[tuple[Path, str]] = []

    for file_path in force_app.rglob("*"):
        if not file_path.is_file():
            continue

        file_type = _classify_file(file_path)
        if file_type is not None:
            files.append((file_path, file_type))

    return files


def list_sfdx_projects(base_path: str | Path) -> list[dict]:
    """List all SFDX projects found under a base directory.

    Returns a list of dicts with project info.
    """
    base = Path(base_path)
    projects = []

    if not base.is_dir():
        return projects

    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue

        # Check if it's an SFDX project
        has_sfdx = (child / "sfdx-project.json").exists()
        has_force_app = (child / "force-app").is_dir()

        if has_sfdx or has_force_app:
            projects.append({
                "name": child.name,
                "path": str(child),
                "has_sfdx_config": has_sfdx,
                "has_force_app": has_force_app,
            })

    return projects
