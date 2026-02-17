"""Anonymization engine for stripping org-specific data from patterns.

Three-level approach:
1. STRUCTURAL anonymization: strips IDs, emails, URLs, dates, money
2. HEURISTIC brand detection: CamelCase analysis, cross-object frequency
3. DICTIONARY brand detection: cross-references field name segments against
   a database of 10K+ known company/org names (SEC EDGAR, Fortune 1000,
   US federal agencies)

The goal: a pattern should reveal WHAT it does structurally,
never WHO it was built for.
"""

from __future__ import annotations

import re
from typing import Any

# ── Salesforce Record ID Detection ──

_SF_ID_PATTERN = re.compile(r"\b[a-zA-Z0-9]{15}(?:[a-zA-Z0-9]{3})?\b")

_SF_ID_PREFIXES = {
    "001", "003", "005", "006", "00Q", "00D", "00e", "00G", "00I",
    "012", "015", "01I", "01p", "01q", "01s", "01t", "01Z",
    "02i", "02s", "035", "03d", "04t",
    "050", "058", "068", "069", "07M", "08s",
    "0Af", "0AP", "500", "570", "701", "800", "801",
}

_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)
_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
_MONEY_PATTERN = re.compile(r"\$[\d,]+\.?\d*")
_DATE_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)?\b"
)

# ── Keys that control anonymization behavior ──

_ANONYMIZE_KEYS = {
    "errorMessage", "description", "label", "helpText",
    "inputText", "outputText", "choiceText",
    "interviewLabel",
}

# Salesforce standard objects and fields - these are NOT proprietary
_STANDARD_OBJECTS = {
    "Account", "Contact", "Lead", "Opportunity", "Case", "Task", "Event",
    "User", "Group", "Profile", "Role", "PermissionSet",
    "Campaign", "CampaignMember", "Contract", "Order", "OrderItem",
    "Product2", "PricebookEntry", "Pricebook2", "Quote", "QuoteLineItem",
    "Solution", "ContentDocument", "ContentVersion", "Attachment",
    "Note", "FeedItem", "FeedComment", "Dashboard", "Report",
    "EmailMessage", "EmailTemplate", "Folder",
    "BusinessHours", "Holiday", "RecordType",
    "Organization", "UserRole", "GroupMember",
    "OpportunityLineItem", "OpportunityContactRole",
    "AccountContactRelation", "ContactPointAddress",
}

_STANDARD_FIELDS = {
    "Id", "Name", "OwnerId", "CreatedById", "CreatedDate",
    "LastModifiedById", "LastModifiedDate", "SystemModstamp",
    "IsDeleted", "RecordTypeId", "CurrencyIsoCode",
    "FirstName", "LastName", "Email", "Phone", "MobilePhone",
    "Title", "Department", "Description", "Website",
    "BillingStreet", "BillingCity", "BillingState", "BillingPostalCode",
    "BillingCountry", "ShippingStreet", "ShippingCity", "ShippingState",
    "ShippingPostalCode", "ShippingCountry",
    "Industry", "AnnualRevenue", "NumberOfEmployees",
    "StageName", "CloseDate", "Amount", "Probability",
    "Type", "Status", "Priority", "Subject",
    "AccountId", "ContactId", "LeadId", "OpportunityId",
    "ParentId", "CaseId", "WhatId", "WhoId",
    "IsActive", "IsClosed", "IsWon",
}


# Salesforce ecosystem / AppExchange ISV products - NOT proprietary to any org.
# Their presence in field names indicates integration requirements, which is
# transferable structural knowledge (e.g. "this pattern needs Marketo").
_SF_ECOSYSTEM_PRODUCTS = {
    # Marketing automation
    "marketo", "mkto", "pardot", "eloqua", "hubspot", "mailchimp",
    "exacttarget", "salesforcemktg",
    # ABM / Intent
    "demandbase", "6sense", "bombora", "terminus", "rollworks", "triblio",
    # Data enrichment / Intelligence
    "zoominfo", "clearbit", "dun", "dnb", "hoovers", "leadiq",
    "lusha", "apollo", "cognism", "seamless", "slintel",
    # Sales engagement
    "outreach", "salesloft", "gong", "chorus", "clari", "groove",
    "xactly", "velocify", "ringdna", "orum",
    # CPQ / Billing
    "conga", "apttus", "docusign", "pandadoc", "zuora",
    "chargebee", "recurly", "avalara",
    # Integration / iPaaS
    "mulesoft", "jitterbit", "informatica", "talend", "workato",
    "tray", "celigo", "boomi", "snaplogic",
    # Social / Communication
    "linkedin", "slack", "twilio", "sendgrid", "ringcentral",
    "vonage", "bandwidth", "plivo", "talkdesk",
    # Support / Service
    "zendesk", "freshdesk", "intercom", "drift", "qualified",
    "livechat", "chatbot", "ada",
    # Analytics / BI
    "tableau", "domo", "looker", "powerbi", "qlik", "sisense",
    # Project / Collaboration
    "jira", "asana", "monday", "smartsheet", "wrike", "basecamp",
    "confluence", "notion",
    # ERP / Finance
    "netsuite", "quickbooks", "xero", "sage", "intacct", "workday",
    "coupa", "ariba", "certify", "expensify",
    # Data quality / Enrichment (AppExchange)
    "ringlead", "cloudingo", "cloudinga", "usergem", "clay",
    "datagrail", "validity", "people", "dupe",
    # Sales enablement / Productivity (AppExchange)
    "showpad", "highspot", "seismic", "calendly", "chili",
    "conga", "formstack", "netdocuments",
    # Document / E-signature
    "docusign", "pandadoc", "adobe", "echosign", "hellosign",
    # Managed package prefixes (namespace__Field__c)
    "npsp", "npe", "hed", "sfims", "dlrs",
    "bizible", "bizible2", "bizibleid",
    "mkto", "mkto_si", "mkto71",
    "x6sense",
    "lsf", "sked", "cventsfdc", "rh2",
    "lnt", "dozisf", "zvc",
}


class BrandScrubber:
    """Detects and replaces business-specific terms with generic labels.

    Usage:
        scrubber = BrandScrubber()
        scrubber.add_terms(["AcmeCloud", "WidgetCo", "NovaTech", "ZetaSync"])
        # OR auto-detect from field names:
        scrubber.auto_detect_brands(field_names)

        clean_text = scrubber.scrub("AcmeCloud_Customer_Status__c")
        # -> "Brand_A_Customer_Status__c"
    """

    def __init__(self) -> None:
        self._brand_map: dict[str, str] = {}  # original_term -> replacement
        self._counter = 0
        self._pattern: re.Pattern | None = None

    def add_terms(self, terms: list[str]) -> None:
        """Add specific brand/business terms to scrub."""
        for term in terms:
            term_clean = term.strip()
            if term_clean and term_clean not in self._brand_map:
                self._counter += 1
                label = _generic_label(self._counter)
                self._brand_map[term_clean] = label
                # Also add common variations
                lower = term_clean.lower()
                upper = term_clean.upper()
                for variant in (term_clean, lower, upper):
                    if variant not in self._brand_map:
                        self._brand_map[variant] = label
        self._rebuild_pattern()

    def auto_detect_brands(self, all_field_names: list[str],
                           org_name: str = "") -> list[str]:
        """Auto-detect likely brand/business terms from field names.

        Three detection strategies:
        1. HEURISTIC: CamelCase compound words that appear as prefixes
           across 2+ objects (e.g., AcmeCloud on Account + Opportunity)
        2. NAMESPACE: Managed package namespace prefixes (mkto_si__, etc.)
        3. DICTIONARY: Cross-reference field segments against a database
           of 10K+ known company/org names (SEC EDGAR, Fortune 1000,
           US federal agencies, universities, hospitals)
        """
        from .company_dict import find_company_matches, is_known_company

        # Track which terms appear as field name PREFIXES, grouped by object
        prefix_objects: dict[str, set[str]] = {}
        # Track managed package namespaces
        namespaces: set[str] = set()
        # Track dictionary matches (company name DB)
        dict_matches: set[str] = set()

        for field in all_field_names:
            if "." in field:
                obj, field_name = field.split(".", 1)
            else:
                obj, field_name = "Unknown", field

            if not field_name.endswith("__c") and not field_name.endswith("__r"):
                continue

            # Detect managed package namespace (e.g., mkto_si__Field__c)
            # Skip known SF ecosystem namespaces - those indicate integrations
            ns_match = re.match(r"^(\w+)__(\w+)__[cr]$", field_name)
            if ns_match:
                ns = ns_match.group(1)
                if (ns.lower() not in _STRUCTURAL_WORDS
                        and not _is_ecosystem_term(ns)
                        and _looks_like_brand_name(ns)):
                    namespaces.add(ns)
                continue

            bare = field_name.replace("__c", "").replace("__r", "")
            parts = bare.split("_")
            if not parts:
                continue

            # ── Strategy 1: Heuristic (CamelCase + cross-object frequency) ──

            # Check the FIRST segment as a potential brand prefix
            prefix = parts[0]
            if (len(prefix) >= 4
                    and prefix.lower() not in _STRUCTURAL_WORDS
                    and not _is_ecosystem_term(prefix)
                    and prefix not in _STANDARD_OBJECTS
                    and prefix not in _STANDARD_FIELDS
                    and _looks_like_brand_name(prefix)):
                prefix_objects.setdefault(prefix, set()).add(obj)

            # Also check ALL segments for CamelCase brand names
            for part in parts[1:]:
                if (len(part) >= 5
                        and part.lower() not in _STRUCTURAL_WORDS
                        and not _is_ecosystem_term(part)
                        and part not in _STANDARD_OBJECTS
                        and part not in _STANDARD_FIELDS
                        and _looks_like_brand_name(part)):
                    prefix_objects.setdefault(part, set()).add(obj)

            # ── Strategy 3: Dictionary (known company names) ──
            # Check individual segments and multi-word combos
            for match in find_company_matches(parts):
                if (match.lower() not in _STRUCTURAL_WORDS
                        and not _is_ecosystem_term(match)):
                    dict_matches.add(match)

        # ── Combine results from all strategies ──

        # Heuristic: require 2+ objects
        seen_lower: set[str] = set()
        detected = []
        for term, objects in sorted(prefix_objects.items(),
                                    key=lambda x: -len(x[1])):
            if len(objects) >= 2 and term.lower() not in seen_lower:
                detected.append(term)
                seen_lower.add(term.lower())

        # Namespaces: always add
        for ns in namespaces:
            if ns.lower() not in seen_lower:
                detected.append(ns)
                seen_lower.add(ns.lower())

        # Dictionary: add if not already detected by heuristic
        for match in sorted(dict_matches):
            if match.lower() not in seen_lower:
                detected.append(match)
                seen_lower.add(match.lower())

        if detected:
            self.add_terms(detected)

        return detected

    def scrub(self, text: str) -> str:
        """Replace all known brand terms in text with generic labels."""
        if not text or not self._brand_map:
            return text
        if self._pattern is None:
            return text

        def _replace(match: re.Match) -> str:
            term = match.group(0)
            # Try exact match first, then case variations
            return (self._brand_map.get(term)
                    or self._brand_map.get(term.lower())
                    or self._brand_map.get(term.capitalize())
                    or f"[BRAND]")

        return self._pattern.sub(_replace, text)

    def _rebuild_pattern(self) -> None:
        """Rebuild the regex pattern from current brand map.

        Uses word-boundary-aware matching to avoid partial matches
        like scrubbing 'Dev' inside 'DeveloperName'.
        """
        if not self._brand_map:
            self._pattern = None
            return
        # Sort by length (longest first) to match greedily
        # Use lookbehind/lookahead for word boundaries that also work
        # with underscores (since SF field names use underscores)
        terms = sorted(self._brand_map.keys(), key=len, reverse=True)
        escaped = [re.escape(t) for t in terms]
        # Match terms that are bounded by underscores, start/end of string,
        # or non-alphanumeric chars
        self._pattern = re.compile(
            r"(?<![a-zA-Z])(?:" + "|".join(escaped) + r")(?![a-zA-Z])",
            re.IGNORECASE,
        )

    @property
    def brand_map(self) -> dict[str, str]:
        return dict(self._brand_map)


def _generic_label(n: int) -> str:
    """Generate a generic label like Brand_A, Brand_B, ..., Brand_AA."""
    if n <= 26:
        return f"Brand_{chr(64 + n)}"
    else:
        return f"Brand_{n}"


def _looks_like_brand_name(term: str) -> bool:
    """Check if a term looks like a product/company name vs a descriptive field name.

    Conservative detection - only flag terms with clear brand indicators:
    - CamelCase inner capitals (AcmeCloud, WidgetCo)
    - ALLCAPS-to-lowercase (NovaTech, ZetaSync)
    - Mixed letters+numbers (bizible2, mkto71)

    Rejects descriptive compound words like IsAPastUser, PastAccount, CreatedById
    by checking if the CamelCase parts decompose into common English/SF words.
    """
    has_camel = bool(re.search(r"[a-z][A-Z]", term))
    has_allcaps_lower = bool(re.search(r"[A-Z]{2,}[a-z]", term)) and len(term) >= 6
    has_mixed_num = (bool(re.search(r"[a-zA-Z]", term))
                     and bool(re.search(r"\d", term)))

    if not (has_camel or has_allcaps_lower or has_mixed_num):
        return False

    # Decompose CamelCase into sub-words and check if they're all common
    # Brand names have unusual sub-words: Acme+Cloud, Widget+Co, User+Gem
    # Descriptive names decompose to common words: Past+Account, Created+By+Id
    if has_camel or has_allcaps_lower:
        parts = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z][a-z]*|[a-z]+", term)
        if len(parts) >= 3:
            # For 3+ part terms, reject if all parts are common words
            common_count = sum(
                1 for p in parts
                if (p.lower() in _COMMON_FIELD_WORDS
                    or p in _STANDARD_OBJECTS
                    or p in _STANDARD_FIELDS)
            )
            if common_count == len(parts):
                return False

    return True


# Common words that appear in Salesforce field names (used to detect
# descriptive compound names vs brand names during CamelCase decomposition)
_COMMON_FIELD_WORDS = {
    # Verbs
    "is", "has", "can", "do", "get", "set", "add", "run", "show", "hide",
    "send", "sync", "find", "check", "create", "update", "delete", "merge",
    "convert", "assign", "match", "evaluate", "calculate", "resolve",
    "start", "stop", "close", "open", "lock", "unlock", "submit", "approve",
    "reject", "cancel", "complete", "process", "handle", "trigger",
    # Adjectives / State
    "new", "old", "past", "current", "previous", "next", "prior", "last",
    "first", "active", "inactive", "primary", "secondary", "default",
    "custom", "standard", "manual", "auto", "mass", "bulk", "no", "longer",
    "within", "target", "matching", "linked", "related", "associated",
    # Nouns (common in field names)
    "account", "contact", "lead", "opportunity", "case", "task", "event",
    "user", "role", "profile", "group", "team", "queue", "member",
    "company", "person", "persona", "firm", "org", "organization", "customer",
    "name", "date", "time", "type", "status", "stage", "step", "phase",
    "score", "rating", "tier", "level", "count", "total", "sum", "amount",
    "number", "record", "field", "value", "key", "index", "code",
    "email", "phone", "address", "city", "state", "country", "street",
    "job", "title", "department", "division", "region", "territory",
    "info", "infos", "data", "note", "notes", "detail", "details",
    "url", "link", "path", "source", "ref", "reference",
    "id", "by", "at", "to", "for", "of", "in", "on", "from", "with",
    # Time-related
    "month", "year", "day", "week", "hour", "quarter", "annual", "daily",
    "created", "modified", "updated", "started", "ended", "closed",
    # SF-specific
    "relationship", "lookup", "master", "detail", "junction", "rollup",
    "formula", "workflow", "approval", "permission", "sharing", "owner",
    "billing", "shipping", "mailing",
}


def _is_ecosystem_term(term: str) -> bool:
    """Check if a term matches or contains a known SF ecosystem product.

    Matches: 'BizibleId' (contains 'bizible'), 'SyncToMarketo' (contains 'marketo'),
    'mkto_si' (exact match), 'X6sense' (contains '6sense').
    """
    lower = term.lower()
    # Exact match
    if lower in _SF_ECOSYSTEM_PRODUCTS:
        return True
    # Check if term contains an ecosystem product name (4+ char to avoid short false matches)
    for eco in _SF_ECOSYSTEM_PRODUCTS:
        if len(eco) >= 4 and eco in lower:
            return True
    return False


# Common structural words that are NOT brand names
_STRUCTURAL_WORDS = {
    "account", "contact", "lead", "opportunity", "case", "user", "task",
    "event", "campaign", "contract", "order", "product", "quote",
    "custom", "field", "type", "status", "date", "time", "number",
    "amount", "count", "total", "sum", "avg", "min", "max",
    "name", "first", "last", "email", "phone", "address", "city",
    "state", "country", "zip", "postal", "code", "street",
    "created", "modified", "updated", "deleted", "active", "inactive",
    "new", "old", "prior", "current", "previous", "next",
    "start", "end", "open", "closed", "won", "lost",
    "primary", "secondary", "main", "default", "standard",
    "record", "lookup", "master", "detail", "junction",
    "auto", "manual", "system", "admin", "owner", "manager",
    "assign", "assigned", "assignment", "group", "member", "queue",
    "territory", "region", "division", "department", "team",
    "score", "rating", "tier", "level", "stage", "step", "phase",
    "data", "migration", "integration", "sync", "batch", "trigger",
    "flow", "process", "automation", "workflow", "rule", "action",
    "validation", "formula", "rollup", "summary", "report", "dashboard",
    "permission", "profile", "role", "sharing", "security",
    "billing", "shipping", "mailing", "physical",
    "annual", "monthly", "weekly", "daily", "quarterly",
    "revenue", "profit", "cost", "price", "discount",
    "marketing", "sales", "service", "support", "operations",
    "onboarding", "customer", "prospect", "partner", "vendor",
    "request", "response", "approval", "rejection",
    "self", "close", "bypass", "override", "exception",
    "trial", "subscription", "license", "renewal",
    "enterprise", "professional", "basic", "premium",
    "update", "insert", "delete", "upsert", "merge",
    "before", "after", "save", "submit",
    "is", "has", "can", "should", "will", "not", "and", "the",
    "get", "set", "put", "run", "send", "check", "find", "resolve",
    "evaluate", "calculate", "determine", "process", "handle",
    "linked", "related", "associated", "parent", "child",
    "person", "firm", "company", "organization", "org",
    "id", "ids", "key", "value", "index", "ref", "reference",
    "null", "blank", "empty", "true", "false", "yes", "no",
    "slack", "message", "notification", "alert", "error", "warning",
    "mql", "sql", "sal", "bdr", "sdr", "ae", "rep",
    "software", "payments", "platform", "app", "application",
    "round", "robin", "config", "setting", "boundary", "matching",
}


# ── Global scrubber instance (configured per-ingest) ──
_active_scrubber: BrandScrubber | None = None


def configure_scrubber(
    org_name: str = "",
    custom_terms: list[str] | None = None,
    field_names: list[str] | None = None,
) -> BrandScrubber:
    """Configure the brand scrubber for an ingestion run.

    Call this before extracting patterns from an org.
    """
    global _active_scrubber
    scrubber = BrandScrubber()

    if custom_terms:
        scrubber.add_terms(custom_terms)

    if field_names:
        scrubber.auto_detect_brands(field_names, org_name)
    elif org_name:
        scrubber.auto_detect_brands([], org_name)

    _active_scrubber = scrubber
    return scrubber


def get_scrubber() -> BrandScrubber | None:
    """Get the currently active brand scrubber."""
    return _active_scrubber


# ── Core anonymization functions ──

def _looks_like_sf_id(value: str) -> bool:
    """Check if a string looks like a Salesforce record ID."""
    if len(value) not in (15, 18):
        return False
    if not value.isalnum():
        return False
    prefix = value[:3]
    return prefix in _SF_ID_PREFIXES or prefix[:2] in ("a0", "a1", "a2", "a3")


def anonymize_string(value: str) -> str:
    """Anonymize a single string value, preserving structural content."""
    if not value or len(value) < 3:
        return value

    result = value

    # Replace Salesforce record IDs
    def _replace_id(match: re.Match) -> str:
        candidate = match.group(0)
        if _looks_like_sf_id(candidate):
            return "[SF_ID]"
        return candidate

    result = _SF_ID_PATTERN.sub(_replace_id, result)
    result = _EMAIL_PATTERN.sub("[EMAIL]", result)
    result = _URL_PATTERN.sub("[URL]", result)
    result = _IP_PATTERN.sub("[IP]", result)
    result = _MONEY_PATTERN.sub("[AMOUNT]", result)

    # Apply brand scrubbing
    scrubber = get_scrubber()
    if scrubber:
        result = scrubber.scrub(result)

    return result


def anonymize_field_name(field_name: str) -> str:
    """Anonymize a custom field API name while preserving its structural type.

    Examples:
        AcmeCloud_Customer_Status__c -> Brand_A_Customer_Status__c
        WidgetCo_Product_Tier__c     -> Brand_B_Product_Tier__c
    """
    scrubber = get_scrubber()
    if scrubber:
        return scrubber.scrub(field_name)
    return field_name


def anonymize_structure(obj: Any, parent_key: str = "") -> Any:
    """Recursively anonymize a pattern structure dict/list.

    - Structural keys (operators, connectors): preserved, brand-scrubbed
    - Content keys (labels, descriptions, error messages): fully anonymized
    - Field references: brand-scrubbed but structure preserved
    """
    if isinstance(obj, str):
        if parent_key in _ANONYMIZE_KEYS:
            return f"[{parent_key.upper()}:{len(obj)}chars]"
        return anonymize_string(obj)

    elif isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            result[key] = anonymize_structure(value, key)
        return result

    elif isinstance(obj, list):
        return [anonymize_structure(item, parent_key) for item in obj]

    else:
        return obj


def extract_field_refs_from_formula(formula: str) -> list[str]:
    """Extract field references from a Salesforce formula string."""
    fields: set[str] = set()

    custom_pattern = re.compile(r"\b(\w+__[cr])\b")
    for match in custom_pattern.finditer(formula):
        fields.add(anonymize_field_name(match.group(1)))

    dollar_pattern = re.compile(r"\$\w+\.(\w+)")
    for match in dollar_pattern.finditer(formula):
        fields.add(anonymize_field_name(match.group(1)))

    obj_field_pattern = re.compile(r"\b([A-Z]\w+)\.([A-Z]\w+)\b")
    for match in obj_field_pattern.finditer(formula):
        field_ref = f"{match.group(1)}.{match.group(2)}"
        fields.add(anonymize_field_name(field_ref))

    return sorted(fields)
