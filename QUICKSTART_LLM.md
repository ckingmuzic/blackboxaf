# Quick Start: LLM Natural Language Search

BlackBoxAF supports natural language search powered by Claude AI. Instead of keyword matching, you can ask questions like:

- `"approval flows with email notification"`
- `"validation rules for email format"`
- `"record-triggered flows that update related objects"`

## Setup

### 1. Get an Anthropic API Key

1. Sign up at [console.anthropic.com](https://console.anthropic.com/)
2. Create an API key and copy it

### 2. Set the Environment Variable

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

**Windows (Permanent):**
```powershell
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'sk-ant-api03-your-key-here', 'User')
```

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
# Add to ~/.bashrc or ~/.zshrc for persistence
```

### 3. Install AI Dependencies

```bash
pip install -e ".[ai]"
```

### 4. Restart BlackBoxAF

```bash
blackboxaf
```

## Usage

### API

```bash
# Natural language search
curl -X POST "http://localhost:8000/api/patterns/search/nl?query=approval flows with email notification"

# Check daily cost
curl http://localhost:8000/api/patterns/search/cost
```

### Response Format

```json
{
  "results": [
    {"id": 42, "name": "Flow: 3-Tier Approval with Email", "...": "..."},
    {"id": 17, "name": "Flow: Approval with Rejection Loop", "...": "..."}
  ],
  "total": 2,
  "query": "approval flows with email notification",
  "method": "llm"
}
```

## Cost

- Uses Claude Haiku (~$0.001-0.003 per search)
- Responses are cached for 24 hours — repeat queries are free
- Built-in daily spending cap ($1.00/day default)
- Falls back to keyword search if no API key is configured

## Troubleshooting

| Error | Fix |
|-------|-----|
| `LLM features require the 'anthropic' package` | `pip install anthropic` |
| `ANTHROPIC_API_KEY environment variable not set` | Set the env var (see step 2 above) |
| `Daily LLM cost limit reached` | Wait until tomorrow, or adjust `_MAX_DAILY_COST` in `src/blackboxaf/api/llm.py` |
| Slow first response (3-5s) | Normal — first query hits the API. Cached queries are instant. |

## Without an API Key

LLM search is optional. Without an API key, BlackBoxAF uses full-text keyword search which works well for most queries. The LLM layer adds semantic understanding on top.
