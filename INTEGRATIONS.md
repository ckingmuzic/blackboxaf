# BlackBoxAF Integrations Guide

Connect your Salesforce Pattern Vault to AI coding assistants and editors.

---

## MCP Server (Claude, Cursor, ChatGPT Desktop, Windsurf)

The MCP (Model Context Protocol) server lets AI assistants search, retrieve, and compose patterns directly.

### Prerequisites
```bash
pip install blackboxaf[mcp]
# or if installed from source:
pip install mcp
```

### Claude Code (CLI)
```bash
claude mcp add blackboxaf -- python -m blackboxaf.mcp_server
```

Then in any conversation:
```
You: Find me approval flow patterns for Opportunity
Claude: [searches your vault via MCP, returns matching patterns]

You: Compose a complete solution for case escalation with SLA tracking
Claude: [uses compose_solution tool, returns multi-component blueprint]
```

### Claude Desktop
Add to your Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json` on Windows, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "blackboxaf": {
      "command": "python",
      "args": ["-m", "blackboxaf.mcp_server"],
      "cwd": "G:\\SFPatternVault"
    }
  }
}
```

Restart Claude Desktop. The vault icon appears in the tools menu.

### Cursor
Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "blackboxaf": {
      "command": "python",
      "args": ["-m", "blackboxaf.mcp_server"]
    }
  }
}
```

### Windsurf
Add to Windsurf MCP settings:

```json
{
  "mcpServers": {
    "blackboxaf": {
      "command": "python",
      "args": ["-m", "blackboxaf.mcp_server"]
    }
  }
}
```

### ChatGPT Desktop
OpenAI has adopted MCP support. Add BlackBoxAF via ChatGPT Desktop settings > Tools > Add MCP Server:
- Command: `python -m blackboxaf.mcp_server`

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `search_patterns` | Search patterns by keyword, category, object, complexity |
| `get_pattern` | Get full pattern detail with structure JSON |
| `list_categories` | List all categories and pattern types |
| `get_vault_stats` | Get vault statistics and breakdowns |
| `compose_solution` | Agentforce-style: compose multi-component solutions from patterns |
| `generate_field_mapping` | Generate field mapping template for adapting a pattern |

### Example MCP Conversations

**Simple search:**
> "Find validation rules for Account objects"

**Agentforce-style composition:**
> "I need a complete approval process for Opportunities over $100K. Include the flow, validation rules, and field definitions."

**Field mapping:**
> "Take pattern #42 and generate a field mapping for my Custom_Invoice__c object"

---

## VS Code Extension

A sidebar panel for browsing, searching, and inserting patterns directly into your SFDX project.

### Install
```bash
# From the .vsix file:
code --install-extension vscode-extension/blackboxaf-0.1.0.vsix
```

Or in VS Code: `Ctrl+Shift+P` > "Extensions: Install from VSIX..." > select the `.vsix` file.

### Prerequisites
The BlackBoxAF server must be running:
```bash
blackboxaf
# or
python -m uvicorn blackboxaf.app:app --port 8000
```

### Features

- **Sidebar browser**: Click the BlackBoxAF icon in the activity bar to browse patterns
- **Search**: Type in the search box or press `Ctrl+Shift+B`
- **Filter**: Filter by category and object using dropdowns
- **Insert at cursor**: Click the arrow button to insert pattern JSON at your cursor position
- **Pattern detail**: Click a pattern name to see full detail, fields, tags, and structure
- **Favorites**: Star patterns and see them in the Favorites panel
- **Compose Solution**: `Ctrl+Shift+P` > "BlackBoxAF: Compose Solution" for Agentforce-style multi-component composition

### Configuration

In VS Code settings (`Ctrl+,`):

| Setting | Default | Description |
|---------|---------|-------------|
| `blackboxaf.serverUrl` | `http://localhost:8000` | BlackBoxAF server URL |
| `blackboxaf.defaultObject` | (empty) | Default object for searches |
| `blackboxaf.pageSize` | `30` | Patterns per page |

---

## ChatGPT Custom GPT (Web)

Create a Custom GPT that can search your pattern vault via the API.

### Setup

1. Go to [ChatGPT](https://chat.openai.com) > Explore GPTs > Create
2. Name: "BlackBoxAF Pattern Vault"
3. Description: "Search and retrieve Salesforce metadata patterns from my BlackBoxAF vault"
4. Instructions:
   ```
   You are a Salesforce pattern search assistant connected to a BlackBoxAF Pattern Vault.
   You can search for reusable metadata patterns (flows, validation rules, Apex, LWC, etc.)
   and help users adapt them to their Salesforce orgs.

   When the user asks about patterns:
   1. Use searchPatterns to find relevant patterns
   2. Use getPattern to get full details
   3. Help the user understand the pattern structure
   4. Suggest field mappings for their target org

   Always explain what each pattern does and how to adapt it.
   ```
5. Actions > Import from URL or paste the OpenAPI spec from `openapi.yaml`
6. Set the server URL to your BlackBoxAF server

### Important Notes
- Your BlackBoxAF server must be accessible from the internet for ChatGPT Actions to work
- For local-only use, consider using ChatGPT Desktop with MCP instead
- Options for exposing locally:
  - **ngrok**: `ngrok http 8000` (temporary public URL)
  - **Cloudflare Tunnel**: `cloudflared tunnel --url http://localhost:8000`
  - **Deploy to cloud**: Run BlackBoxAF on a VPS/cloud instance

---

## OpenAI Agents SDK

Use BlackBoxAF as a tool in custom OpenAI agents:

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async def main():
    server = MCPServerStdio(
        command="python",
        args=["-m", "blackboxaf.mcp_server"],
    )

    agent = Agent(
        name="Salesforce Architect",
        instructions="You help build Salesforce solutions using patterns from BlackBoxAF.",
        mcp_servers=[server],
    )

    result = await Runner.run(agent, "Find me flow patterns for Case escalation")
    print(result.final_output)
```

---

## Agentforce Integration Concept

BlackBoxAF's `compose_solution` tool mirrors Salesforce Agentforce's autonomous agent paradigm:

1. **User gives high-level requirement** → "Build opportunity approval with email notification"
2. **Agent searches pattern vault** → Finds matching flows, validations, fields, layouts
3. **Agent composes solution** → Returns structured blueprint with all components
4. **Agent generates artifacts** → Field mappings, XML templates, deployment instructions

This works across all MCP-compatible platforms (Claude, Cursor, ChatGPT Desktop, Windsurf).

### Example Agentforce-style Workflow

```
User: "I need a complete lead qualification process for my org"

Agent (via compose_solution):
├── Flow Logic (3 patterns)
│   ├── [142] Lead scoring flow with field-based criteria
│   ├── [87]  Lead assignment with round-robin
│   └── [203] Lead conversion with opportunity creation
├── Data Validation (2 patterns)
│   ├── [56]  Required fields validation before conversion
│   └── [89]  Email format + phone format validation
├── Data Model (4 patterns)
│   ├── [12]  Lead custom fields (score, source, campaign)
│   ├── [34]  Lead-to-Account mapping fields
│   └── ...
└── Page Layout (1 pattern)
    └── [178] Lead detail layout with scoring section

Next: Use get_pattern(id) for each, then generate_field_mapping()
```

---

## Troubleshooting

### MCP server won't start
```bash
# Test manually:
python -m blackboxaf.mcp_server
# Should start without errors (waits for stdin)

# Check database exists:
ls data/blackboxaf.db
```

### VS Code extension can't connect
1. Make sure the BlackBoxAF server is running (`blackboxaf` or `python -m uvicorn blackboxaf.app:app --port 8000`)
2. Check the server URL in settings: `Ctrl+,` > search "blackboxaf"
3. Default is `http://localhost:8000`

### ChatGPT Actions timeout
- ChatGPT has a 45-second timeout for actions
- AI search (NL) may be slow on first call - subsequent calls are cached
- Use keyword search for faster results

### "No patterns found"
- Make sure you've ingested at least one SFDX project
- Open `http://localhost:8000` in browser to verify patterns exist
