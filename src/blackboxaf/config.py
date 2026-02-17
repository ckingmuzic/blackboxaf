"""Application configuration.

Handles paths for both development (pip install -e .) and
frozen/bundled mode (PyInstaller .exe).
"""

import sys
from pathlib import Path

# Detect if we're running as a PyInstaller bundle
FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    # PyInstaller unpacks data files to sys._MEIPASS
    _BUNDLE_DIR = Path(sys._MEIPASS)
    FRONTEND_DIR = _BUNDLE_DIR / "frontend"
    # Store DB next to the .exe so it persists across runs
    _EXE_DIR = Path(sys.executable).parent
    DATA_DIR = _EXE_DIR / "data"
else:
    FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
    # In development, store DB in the project root's data/ dir
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "data"

DB_PATH = DATA_DIR / "blackboxaf.db"

# Salesforce API version considered "current"
CURRENT_SF_API_VERSION = "62.0"

# Pattern type -> display category mapping
CATEGORY_MAP = {
    "flow_decision": "Flow Logic",
    "flow_record_lookup": "Flow Logic",
    "flow_record_update": "Flow Logic",
    "flow_record_create": "Flow Logic",
    "flow_record_delete": "Flow Logic",
    "flow_screen": "Flow Logic",
    "flow_assignment": "Flow Logic",
    "flow_loop": "Flow Logic",
    "flow_subflow": "Flow Logic",
    "flow_action_call": "Flow Logic",
    "flow_formula": "Flow Logic",
    "flow_full": "Flow Logic",
    "validation_rule": "Data Validation",
    "object_definition": "Data Model",
    "field_definition": "Data Model",
    "lwc_component": "UI Component",
    "aura_component": "UI Component",
    "report_definition": "Reporting",
    "report_formula": "Reporting",
    "dashboard_definition": "Reporting",
    "layout_definition": "Page Layout",
    "apex_class": "Apex Logic",
    "apex_trigger": "Apex Logic",
}

# Color codes for UI display per category
CATEGORY_COLORS = {
    "Flow Logic": "#3b82f6",       # blue
    "Data Validation": "#22c55e",  # green
    "Data Model": "#a855f7",       # purple
    "UI Component": "#f97316",     # orange
    "Reporting": "#eab308",        # yellow
    "Page Layout": "#06b6d4",     # cyan
    "Apex Logic": "#ef4444",       # red
}
