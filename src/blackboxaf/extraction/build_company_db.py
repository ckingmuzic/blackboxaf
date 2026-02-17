"""Build the company names dictionary from public data sources.

Downloads and processes:
- SEC EDGAR company_tickers.json (publicly traded companies)
- Fortune 500/1000 CSV (top US companies)
- CISA dotgov-data (US federal agencies)

Output: data/company_names.txt (one name per line, lowercase, sorted)

Usage:
    python -m blackboxaf.extraction.build_company_db
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"
_OUTPUT = _DATA_DIR / "company_names.txt"

# Suffixes to strip from company names to get the core brand name
_SUFFIXES = [
    " incorporated", " inc.", " inc", " corporation", " corp.", " corp",
    " company", " co.", " co", " llc", " ltd.", " ltd", " l.p.", " lp",
    " plc", " group", " holdings", " holding", " international", " intl",
    " n.a.", " s.a.", " ag", " se", " nv", " & co.", " & co",
    " enterprises", " industries", " solutions", " services", " technologies",
    " technology", " partners", " associates", " financial", " bancorp",
    " bancshares", " bankcorp", " brands", " systems", " networks",
    " communications", " health", " healthcare", " pharma", " therapeutics",
    " biosciences", " sciences", " labs", " laboratories",
    " de", " sa", " spa", " gmbh", " pty", " bv",
]

# Words too generic to be a useful company match on their own
_TOO_GENERIC = {
    "the", "a", "an", "and", "or", "of", "for", "in", "on", "at", "to",
    "new", "old", "first", "one", "two", "three", "four", "five",
    "north", "south", "east", "west", "central",
    "northern", "southern", "eastern", "western",
    "american", "national", "international", "global", "united", "general",
    "federal", "state", "city", "county", "royal", "imperial",
    "pacific", "atlantic", "continental",
    "premier", "standard", "liberty", "freedom", "patriot", "guardian",
    "advance", "advanced", "progressive", "select", "prime", "mutual",
    "trust", "fidelity", "pioneer", "heritage", "legacy",
    "energy", "power", "solar", "wind", "gas", "oil", "fuel",
    "bank", "financial", "capital", "fund", "credit", "insurance",
    "health", "medical", "care", "life", "bio",
    "tech", "digital", "data", "cloud", "cyber", "software", "web",
    "media", "communications", "wireless", "mobile",
    "group", "holding", "management", "consulting", "advisory",
    "service", "services", "solutions", "systems", "resources",
    "development", "research", "innovation", "design",
    "home", "house", "land", "real", "estate", "property",
    "food", "foods", "restaurant", "dining",
    "auto", "motor", "motors", "transport", "logistics", "freight",
    "air", "airlines", "aviation", "marine",
    "steel", "iron", "metal", "metals", "mining", "materials",
    "chemical", "chemicals", "industrial", "industries",
    "retail", "store", "stores", "mart", "market", "shop",
    "info", "plus", "pro", "max", "core", "base", "hub", "link", "net",
    "true", "sure", "best", "top", "peak", "apex", "summit", "vertex",
    "quest", "spark", "pulse", "wave", "flow", "stream",
    "bridge", "harbor", "beacon", "compass", "horizon", "frontier",
    "spectrum", "genesis", "nova", "terra", "nexus",
    "diamond", "sterling", "gold", "silver", "platinum",
    "star", "sun", "moon", "sky", "ocean", "river", "lake",
    "eagle", "hawk", "falcon", "lion", "wolf", "bear",
    "red", "blue", "green", "black", "white", "grey", "gray",
    "alpha", "beta", "delta", "sigma", "omega",
    "office", "bureau", "department", "division", "agency", "commission",
    "board", "council", "committee", "authority", "administration",
    "institute", "institution", "center", "centre", "foundation",
    "association", "society", "organization", "federation", "alliance",
    "university", "college", "school", "academy",
    # Common Salesforce / CRM field words (must not trigger false positives)
    "status", "custom", "direct", "form", "forms", "field", "fields",
    "record", "records", "report", "reports", "contact", "contacts",
    "account", "accounts", "order", "orders", "product", "products",
    "asset", "assets", "quote", "quotes", "price", "value", "values",
    "source", "target", "owner", "parent", "child", "master", "detail",
    "active", "total", "count", "amount", "number", "index", "level",
    "stage", "phase", "score", "rating", "model", "method", "process",
    "action", "actions", "event", "events", "alert", "alerts",
    "template", "templates", "batch", "queue", "trigger", "logic",
    "update", "create", "delete", "merge", "convert", "transfer",
    "close", "closed", "review", "approve", "reject", "submit",
    "enable", "enabled", "disable", "disabled",
    "import", "export", "sync", "async", "audit", "track", "trace",
    "access", "permission", "share", "shared", "public", "private",
    "internal", "external", "inbound", "outbound", "primary", "backup",
    "current", "previous", "original", "initial", "final", "pending",
    "complete", "completed", "partial", "draft",
    "annual", "monthly", "weekly", "daily", "quarter", "fiscal",
    "region", "territory", "district", "segment", "sector", "market",
    "standard", "premium", "basic", "trial", "pilot", "express",
    "response", "request", "notice", "renewal", "invoice", "payment",
    "credit", "debit", "balance", "limit",
    "vision", "mission", "focus", "impact", "insight", "connect",
    "advance", "progress", "success", "resolve", "achieve", "engage",
    "encore", "merit", "integrity", "summit",
    "contract", "vendor", "partner", "client", "prospect", "campaign",
    "batch", "schedule", "trigger", "method", "workflow",
    "scientific", "diagnostic", "precision", "applied", "venture",
}


def _strip_suffixes(name: str) -> str:
    """Strip corporate suffixes from a company name."""
    lower = name.lower().strip()
    # Remove trailing punctuation
    lower = lower.rstrip(".,;")
    for suffix in sorted(_SUFFIXES, key=len, reverse=True):
        if lower.endswith(suffix):
            lower = lower[: -len(suffix)].strip().rstrip(",.")
            break
    return lower


def _normalize(name: str) -> str:
    """Normalize a company name for dictionary storage."""
    # Remove special characters but keep spaces and hyphens
    clean = re.sub(r"[^\w\s\-&]", "", name)
    # Collapse whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean.lower()


def _extract_sec_names(path: Path) -> set[str]:
    """Extract company names from SEC EDGAR tickers JSON."""
    names = set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for entry in data.values():
        title = entry.get("title", "").strip()
        if not title or len(title) < 3:
            continue

        # Add full name (normalized)
        full = _normalize(title)
        if full and len(full) >= 3:
            names.add(full)

        # Add stripped name (without Corp/Inc/etc.)
        stripped = _strip_suffixes(title)
        stripped = _normalize(stripped)
        if stripped and len(stripped) >= 3:
            names.add(stripped)

        # Add ticker (only 4+ chars to avoid false positives)
        ticker = entry.get("ticker", "").strip()
        if ticker and len(ticker) >= 4:
            names.add(ticker.lower())

    return names


def _extract_fortune_names(path: Path) -> set[str]:
    """Extract company names from Fortune CSV."""
    names = set()
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Try different column names
            name = (row.get("company") or row.get("name") or "").strip()
            if not name or len(name) < 3:
                continue

            full = _normalize(name)
            if full:
                names.add(full)

            stripped = _strip_suffixes(name)
            stripped = _normalize(stripped)
            if stripped and len(stripped) >= 3:
                names.add(stripped)
    return names


def _extract_gov_agencies(path: Path) -> set[str]:
    """Extract organization names from federal domains CSV."""
    names = set()
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            org = (row.get("Organization name") or "").strip()
            if not org or len(org) < 4:
                continue

            full = _normalize(org)
            if full:
                names.add(full)

            # Also add acronym if org name has 2+ capitalized words
            words = org.split()
            if len(words) >= 2:
                acronym = "".join(w[0] for w in words if w[0].isupper())
                if len(acronym) >= 3:
                    names.add(acronym.lower())

            # Add sub-org too
            sub = (row.get("Suborganization name") or "").strip()
            if sub and len(sub) >= 4:
                names.add(_normalize(sub))

    return names


def _extract_distinctive_words(names: set[str]) -> set[str]:
    """Extract distinctive individual words from multi-word company names.

    For "Teladoc Health Inc", extracts "teladoc" (unusual word).
    For "Direct Energy", extracts "direct energy" as combined but NOT
    "direct" or "energy" alone (too generic).

    Only extracts words that are 5+ chars and NOT in the generic set.
    """
    words = set()
    for name in names:
        parts = name.split()
        if len(parts) < 2:
            continue
        for part in parts:
            clean = part.strip(".,;-&")
            if (len(clean) >= 5
                    and clean not in _TOO_GENERIC
                    and not clean.isdigit()):
                words.add(clean)
    return words


def _filter_names(names: set[str]) -> set[str]:
    """Filter out names that are too generic to be useful."""
    filtered = set()
    for name in names:
        # Skip very short names
        if len(name) < 3:
            continue
        # Skip if the name IS a generic word
        if name in _TOO_GENERIC:
            continue
        filtered.add(name)
    return filtered


def build() -> int:
    """Build the company names dictionary. Returns count of names."""
    sec_names = set()
    fortune_names = set()
    gov_names = set()

    # SEC EDGAR
    sec_path = _DATA_DIR / "sec_tickers.json"
    if sec_path.exists():
        sec_names = _extract_sec_names(sec_path)
        print(f"  SEC EDGAR:       {len(sec_names):>6} names")

    # Fortune 500
    f500_path = _DATA_DIR / "fortune500.csv"
    if f500_path.exists():
        fortune_names |= _extract_fortune_names(f500_path)

    # Fortune 1000
    f1000_path = _DATA_DIR / "fortune1000.csv"
    if f1000_path.exists():
        fortune_names |= _extract_fortune_names(f1000_path)
    print(f"  Fortune 500/1000:{len(fortune_names):>6} names")

    # Federal agencies
    gov_path = _DATA_DIR / "federal_domains.csv"
    if gov_path.exists():
        gov_names = _extract_gov_agencies(gov_path)
        print(f"  Federal agencies:{len(gov_names):>6} names")

    # Combine all sources
    all_names = sec_names | fortune_names | gov_names
    print(f"  Combined (raw):  {len(all_names):>6} names")

    # Extract distinctive individual words from multi-word names
    # e.g., "Teladoc Health" -> also adds "teladoc"
    distinctive = _extract_distinctive_words(all_names)
    print(f"  Distinctive words:{len(distinctive):>5} extracted")
    all_names |= distinctive

    filtered = _filter_names(all_names)
    print(f"  After filtering: {len(filtered):>6} names")

    # Write sorted output
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT, "w", encoding="utf-8") as f:
        f.write(f"# Company names dictionary - {len(filtered)} entries\n")
        f.write("# Sources: SEC EDGAR, Fortune 500/1000, US Federal Agencies\n")
        f.write("# Generated by: python -m blackboxaf.extraction.build_company_db\n")
        f.write("#\n")
        for name in sorted(filtered):
            f.write(f"{name}\n")

    print(f"\n  Written to: {_OUTPUT}")
    print(f"  Total unique names: {len(filtered)}")
    return len(filtered)


if __name__ == "__main__":
    print("Building company names dictionary...")
    build()
