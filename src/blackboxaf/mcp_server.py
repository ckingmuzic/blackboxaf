"""BlackBoxAF MCP Server - Pattern Vault for AI coding assistants.

Exposes Salesforce pattern search, retrieval, and composition tools
via the Model Context Protocol (MCP). Works with:
- Claude Code / Claude Desktop
- Cursor / Windsurf
- ChatGPT Desktop (MCP support)
- Any MCP-compatible AI tool

Usage:
    python -m blackboxaf.mcp_server

Configure in Claude Code:
    claude mcp add blackboxaf -- python -m blackboxaf.mcp_server
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Add src to path so imports work when run standalone
_src = str(Path(__file__).resolve().parent.parent)
if _src not in sys.path:
    sys.path.insert(0, _src)

from blackboxaf.db.database import get_session_factory, init_db
from blackboxaf.db.models import Pattern, Source
from blackboxaf.config import CATEGORY_COLORS

from sqlalchemy import func, text


# ── Server Setup ──

server = Server("blackboxaf")

def _get_session():
    """Get a database session."""
    engine = init_db()
    factory = get_session_factory(engine)
    return factory()


# ── Tool Definitions ──

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_patterns",
            description=(
                "Search the BlackBoxAF Salesforce pattern vault. "
                "Finds reusable metadata patterns (flows, validation rules, "
                "Apex classes, LWC components, reports, layouts, object/field configs) "
                "extracted from real Salesforce orgs. Use keyword or natural language queries."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - keywords or natural language (e.g. 'approval flow with email', 'opportunity validation rules', 'account field patterns')",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category",
                        "enum": ["Flow Logic", "Data Validation", "Data Model", "UI Component", "Reporting", "Page Layout", "Apex Logic"],
                    },
                    "pattern_type": {
                        "type": "string",
                        "description": "Filter by specific pattern type (e.g. 'flow_decision', 'validation_rule', 'apex_class')",
                    },
                    "source_object": {
                        "type": "string",
                        "description": "Filter by Salesforce object (e.g. 'Account', 'Opportunity', 'Case')",
                    },
                    "min_complexity": {
                        "type": "integer",
                        "description": "Minimum complexity score (1-5)",
                        "minimum": 1,
                        "maximum": 5,
                    },
                    "max_complexity": {
                        "type": "integer",
                        "description": "Maximum complexity score (1-5)",
                        "minimum": 1,
                        "maximum": 5,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_pattern",
            description=(
                "Get the full detail of a specific pattern by ID, including "
                "its complete structure (JSON), field references, tags, and metadata. "
                "Use this after search_patterns to get the full pattern data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_id": {
                        "type": "integer",
                        "description": "The pattern ID from search results",
                    },
                },
                "required": ["pattern_id"],
            },
        ),
        Tool(
            name="list_categories",
            description=(
                "List all available pattern categories and their counts. "
                "Use this to understand what types of patterns are in the vault."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_vault_stats",
            description=(
                "Get overall statistics about the pattern vault - total patterns, "
                "breakdown by category/type/object, complexity distribution, and sources."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="compose_solution",
            description=(
                "Agentforce-style autonomous composition. Given a high-level Salesforce "
                "requirement, searches the pattern vault and assembles a complete solution "
                "from matching patterns across multiple categories (flows, validations, "
                "fields, layouts, etc.). Returns a structured solution blueprint with "
                "all component patterns and their relationships."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "requirement": {
                        "type": "string",
                        "description": "High-level Salesforce requirement (e.g. 'Build an opportunity approval process with manager notification and status tracking')",
                    },
                    "target_object": {
                        "type": "string",
                        "description": "Primary Salesforce object for the solution (e.g. 'Opportunity', 'Case')",
                    },
                    "include_fields": {
                        "type": "boolean",
                        "description": "Include field/object patterns in the solution",
                        "default": True,
                    },
                    "include_flows": {
                        "type": "boolean",
                        "description": "Include flow patterns",
                        "default": True,
                    },
                    "include_validations": {
                        "type": "boolean",
                        "description": "Include validation rule patterns",
                        "default": True,
                    },
                    "include_layouts": {
                        "type": "boolean",
                        "description": "Include page layout patterns",
                        "default": True,
                    },
                },
                "required": ["requirement", "target_object"],
            },
        ),
        Tool(
            name="generate_field_mapping",
            description=(
                "Generate a field mapping template for adapting a pattern to a new org. "
                "Takes a pattern ID and target object, returns a mapping of source fields "
                "to suggested target fields that you can customize."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_id": {
                        "type": "integer",
                        "description": "The pattern ID to generate mapping for",
                    },
                    "target_object": {
                        "type": "string",
                        "description": "Target Salesforce object name",
                    },
                },
                "required": ["pattern_id", "target_object"],
            },
        ),
    ]


# ── Tool Implementations ──

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_patterns":
        return await _search_patterns(arguments)
    elif name == "get_pattern":
        return await _get_pattern(arguments)
    elif name == "list_categories":
        return await _list_categories(arguments)
    elif name == "get_vault_stats":
        return await _get_vault_stats(arguments)
    elif name == "compose_solution":
        return await _compose_solution(arguments)
    elif name == "generate_field_mapping":
        return await _generate_field_mapping(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _search_patterns(args: dict) -> list[TextContent]:
    """Search patterns with filters and FTS."""
    query_text = args.get("query", "")
    category = args.get("category")
    pattern_type = args.get("pattern_type")
    source_object = args.get("source_object")
    min_complexity = args.get("min_complexity")
    max_complexity = args.get("max_complexity")
    limit = args.get("limit", 10)

    session = _get_session()
    try:
        query = session.query(Pattern)

        if category:
            query = query.filter(Pattern.category == category)
        if pattern_type:
            query = query.filter(Pattern.pattern_type == pattern_type)
        if source_object:
            query = query.filter(Pattern.source_object == source_object)
        if min_complexity is not None:
            query = query.filter(Pattern.complexity_score >= min_complexity)
        if max_complexity is not None:
            query = query.filter(Pattern.complexity_score <= max_complexity)

        # Full-text search
        if query_text:
            fts_ids = session.execute(
                text("SELECT row_id FROM patterns_fts WHERE patterns_fts MATCH :q"),
                {"q": query_text},
            ).fetchall()
            matching_ids = [row[0] for row in fts_ids]

            if matching_ids:
                query = query.filter(Pattern.id.in_(matching_ids))
            else:
                like_q = f"%{query_text}%"
                query = query.filter(
                    (Pattern.name.ilike(like_q))
                    | (Pattern.description.ilike(like_q))
                    | (Pattern.source_object.ilike(like_q))
                    | (Pattern.tags.ilike(like_q))
                )

        total = query.count()
        patterns = (
            query.order_by(Pattern.complexity_score.desc(), Pattern.name)
            .limit(limit)
            .all()
        )

        results = []
        for p in patterns:
            results.append({
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "pattern_type": p.pattern_type,
                "source_object": p.source_object,
                "complexity": p.complexity_score,
                "description": p.description[:200] if p.description else "",
                "tags": p.get_tags()[:8],
            })

        output = f"Found {total} patterns (showing {len(results)}):\n\n"
        for r in results:
            output += (
                f"  [{r['id']}] {r['name']}\n"
                f"      Category: {r['category']} | Type: {r['pattern_type']}\n"
                f"      Object: {r['source_object']} | Complexity: {'*' * r['complexity']}\n"
                f"      {r['description']}\n"
                f"      Tags: {', '.join(r['tags'])}\n\n"
            )

        if not results:
            output = f"No patterns found matching '{query_text}'. Try broader keywords or different filters."

        return [TextContent(type="text", text=output)]
    finally:
        session.close()


async def _get_pattern(args: dict) -> list[TextContent]:
    """Get full pattern detail."""
    pattern_id = args.get("pattern_id")

    session = _get_session()
    try:
        pattern = session.query(Pattern).filter_by(id=pattern_id).first()
        if not pattern:
            return [TextContent(type="text", text=f"Pattern {pattern_id} not found.")]

        data = pattern.to_dict()
        output = (
            f"Pattern #{data['id']}: {data['name']}\n"
            f"{'=' * 60}\n"
            f"Category:    {data['category']}\n"
            f"Type:        {data['pattern_type']}\n"
            f"Object:      {data['source_object']}\n"
            f"Complexity:  {data['complexity_score']}/5\n"
            f"API Version: {data['api_version'] or 'N/A'}\n"
            f"Source File: {data['source_file']}\n"
            f"Uses:        {data['use_count']}\n"
            f"\nDescription:\n{data['description']}\n"
            f"\nField References:\n{json.dumps(data['field_references'], indent=2)}\n"
            f"\nTags: {', '.join(data['tags'])}\n"
            f"\nStructure (JSON):\n{json.dumps(data['structure'], indent=2)}\n"
        )

        # Increment use count
        pattern.use_count += 1
        session.commit()

        return [TextContent(type="text", text=output)]
    finally:
        session.close()


async def _list_categories(args: dict) -> list[TextContent]:
    """List categories with counts."""
    session = _get_session()
    try:
        results = (
            session.query(Pattern.category, func.count(Pattern.id))
            .group_by(Pattern.category)
            .order_by(func.count(Pattern.id).desc())
            .all()
        )

        total = sum(c for _, c in results)
        output = f"BlackBoxAF Pattern Vault - {total} total patterns\n\n"
        output += "Categories:\n"
        for cat, count in results:
            color = CATEGORY_COLORS.get(cat, "#888")
            output += f"  {cat}: {count} patterns ({color})\n"

        # Also show pattern types
        types = (
            session.query(Pattern.pattern_type, func.count(Pattern.id))
            .group_by(Pattern.pattern_type)
            .order_by(func.count(Pattern.id).desc())
            .all()
        )
        output += "\nPattern Types:\n"
        for ptype, count in types:
            output += f"  {ptype}: {count}\n"

        return [TextContent(type="text", text=output)]
    finally:
        session.close()


async def _get_vault_stats(args: dict) -> list[TextContent]:
    """Get vault statistics."""
    session = _get_session()
    try:
        total = session.query(Pattern).count()

        by_category = (
            session.query(Pattern.category, func.count(Pattern.id))
            .group_by(Pattern.category).all()
        )
        by_object = (
            session.query(Pattern.source_object, func.count(Pattern.id))
            .group_by(Pattern.source_object)
            .order_by(func.count(Pattern.id).desc())
            .limit(15).all()
        )
        by_complexity = (
            session.query(Pattern.complexity_score, func.count(Pattern.id))
            .group_by(Pattern.complexity_score).all()
        )
        sources = session.query(Source).all()

        output = f"BlackBoxAF Vault Statistics\n{'=' * 40}\n"
        output += f"Total Patterns: {total}\n\n"

        output += "By Category:\n"
        for cat, count in by_category:
            output += f"  {cat}: {count}\n"

        output += "\nTop Objects:\n"
        for obj, count in by_object:
            output += f"  {obj}: {count}\n"

        output += "\nComplexity Distribution:\n"
        for score, count in sorted(by_complexity):
            label = ["", "Basic", "Simple", "Moderate", "Complex", "Expert"][min(score, 5)]
            output += f"  {score} ({label}): {count}\n"

        output += f"\nIngested Sources: {len(sources)}\n"
        for s in sources:
            output += f"  {s.display_name}: {s.pattern_count} patterns\n"

        return [TextContent(type="text", text=output)]
    finally:
        session.close()


async def _compose_solution(args: dict) -> list[TextContent]:
    """Agentforce-style: compose a multi-component solution from patterns."""
    requirement = args.get("requirement", "")
    target_object = args.get("target_object", "")
    include_fields = args.get("include_fields", True)
    include_flows = args.get("include_flows", True)
    include_validations = args.get("include_validations", True)
    include_layouts = args.get("include_layouts", True)

    session = _get_session()
    try:
        # Extract keywords from requirement for search
        keywords = _extract_keywords(requirement)
        solution_components = {}

        # Search each category that's enabled
        category_map = []
        if include_flows:
            category_map.append(("Flow Logic", "Flows"))
        if include_validations:
            category_map.append(("Data Validation", "Validation Rules"))
        if include_fields:
            category_map.append(("Data Model", "Fields & Objects"))
        if include_layouts:
            category_map.append(("Page Layout", "Page Layouts"))

        for category, label in category_map:
            query = session.query(Pattern).filter(Pattern.category == category)

            # Filter by target object if possible
            object_patterns = query.filter(
                Pattern.source_object.ilike(f"%{target_object}%")
            ).all()

            # Also search by keywords across all objects in this category
            keyword_patterns = []
            for kw in keywords:
                like_kw = f"%{kw}%"
                kw_results = query.filter(
                    (Pattern.name.ilike(like_kw))
                    | (Pattern.description.ilike(like_kw))
                    | (Pattern.tags.ilike(like_kw))
                ).limit(5).all()
                keyword_patterns.extend(kw_results)

            # Deduplicate and rank
            seen_ids = set()
            ranked = []
            for p in object_patterns + keyword_patterns:
                if p.id not in seen_ids:
                    seen_ids.add(p.id)
                    ranked.append(p)

            # Sort by complexity (most complete first) and take top 5
            ranked.sort(key=lambda p: p.complexity_score, reverse=True)
            solution_components[label] = ranked[:5]

        # Build solution output
        output = (
            f"Solution Blueprint: {requirement}\n"
            f"{'=' * 60}\n"
            f"Target Object: {target_object}\n"
            f"Keywords: {', '.join(keywords)}\n\n"
        )

        total_components = 0
        for label, patterns in solution_components.items():
            output += f"\n--- {label} ({len(patterns)} patterns) ---\n"
            if not patterns:
                output += "  No matching patterns found. Consider creating custom.\n"
                continue

            for p in patterns:
                total_components += 1
                output += (
                    f"\n  [{p.id}] {p.name}\n"
                    f"      Object: {p.source_object} | Complexity: {p.complexity_score}/5\n"
                    f"      {(p.description or '')[:150]}\n"
                    f"      Fields: {', '.join(p.get_field_references()[:5])}\n"
                )

        output += (
            f"\n{'=' * 60}\n"
            f"Total Components: {total_components}\n\n"
            f"Next Steps:\n"
            f"1. Use get_pattern(id) to retrieve full structure for each component\n"
            f"2. Use generate_field_mapping(id, '{target_object}') to map fields\n"
            f"3. Adapt the pattern structures to your target org's field names\n"
            f"4. Deploy via SFDX or Metadata API\n"
        )

        return [TextContent(type="text", text=output)]
    finally:
        session.close()


async def _generate_field_mapping(args: dict) -> list[TextContent]:
    """Generate field mapping template for a pattern."""
    pattern_id = args.get("pattern_id")
    target_object = args.get("target_object", "")

    session = _get_session()
    try:
        pattern = session.query(Pattern).filter_by(id=pattern_id).first()
        if not pattern:
            return [TextContent(type="text", text=f"Pattern {pattern_id} not found.")]

        fields = pattern.get_field_references()
        source_object = pattern.source_object

        output = (
            f"Field Mapping Template\n"
            f"{'=' * 60}\n"
            f"Pattern: {pattern.name} (#{pattern.id})\n"
            f"Source Object: {source_object}\n"
            f"Target Object: {target_object}\n\n"
            f"Field Mappings (source → target):\n"
            f"{'-' * 40}\n"
        )

        mapping = {}
        for field in fields:
            # Suggest target field name based on source
            if "__c" in field:
                # Custom field - suggest same name on target object
                suggested = field
            elif "." in field:
                # Related field - adjust object reference
                parts = field.split(".")
                suggested = f"{target_object}.{parts[-1]}" if len(parts) > 1 else field
            else:
                # Standard field - keep as-is
                suggested = field

            mapping[field] = suggested
            output += f"  {field:40s} → {suggested}\n"

        output += (
            f"\n{'-' * 40}\n"
            f"Total Fields: {len(fields)}\n\n"
            f"Instructions:\n"
            f"1. Review each mapping above\n"
            f"2. Replace custom field names (__c) with your org's field API names\n"
            f"3. Verify relationship fields point to correct objects\n"
            f"4. Standard fields (Name, Id, etc.) usually map 1:1\n"
        )

        # Include the structure for reference
        output += f"\nPattern Structure (for reference):\n{json.dumps(pattern.get_structure(), indent=2)}\n"

        return [TextContent(type="text", text=output)]
    finally:
        session.close()


def _extract_keywords(text_input: str) -> list[str]:
    """Extract meaningful keywords from a requirement string."""
    stop_words = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "can", "need", "must",
        "that", "this", "these", "those", "i", "we", "you", "it", "they",
        "me", "him", "her", "us", "them", "my", "your", "his", "its",
        "our", "their", "what", "which", "who", "whom", "when", "where",
        "why", "how", "all", "each", "every", "both", "few", "more",
        "most", "other", "some", "such", "no", "not", "only", "same",
        "so", "than", "too", "very", "just", "build", "create", "make",
        "add", "implement", "setup", "configure",
    }

    words = text_input.lower().split()
    keywords = [w.strip(".,!?;:()") for w in words if w.strip(".,!?;:()") not in stop_words]
    # Keep unique, preserve order
    seen = set()
    unique = []
    for kw in keywords:
        if kw and kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique[:10]


# ── Entry Point ──

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
