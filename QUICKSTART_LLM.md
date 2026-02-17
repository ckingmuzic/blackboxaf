# Quick Start: LLM Natural Language Search

## What You Just Got

✅ **Natural language search** - Ask "approval flows with email notification", get relevant patterns
✅ **Cost-optimized** - Uses Claude Haiku ($0.25/1M tokens), caches responses, $1/day limit
✅ **Zero-config for free tier** - Falls back to keyword search if no API key
✅ **Ready to launch** - Just add your Anthropic API key

---

## Setup (2 Minutes)

### 1. Get API Key (Free)
1. Go to https://console.anthropic.com/
2. Sign up (no credit card needed for $5 free credit)
3. Create API key → Copy it

### 2. Set Environment Variable

**Windows (PowerShell)**:
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

**Windows (Permanent)**:
```powershell
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'sk-ant-api03-your-key-here', 'User')
```

**Linux/Mac**:
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

---

## How to Use

### Via API
```bash
# Natural language search
curl -X POST "http://localhost:8000/api/patterns/search/nl?query=approval flows with email notification"

# Check today's cost
curl http://localhost:8000/api/patterns/search/cost
```

### Example Queries
- `"approval flows with email notification"`
- `"validation rules for email format"`
- `"record-triggered flows that update related objects"`
- `"complex flows with multiple decisions"`
- `"simple validation rules for required fields"`

### Response Format
```json
{
  "results": [
    {"id": 42, "name": "Flow: 3-Tier Approval with Email", ...},
    {"id": 17, "name": "Flow: Approval with Rejection Loop", ...}
  ],
  "total": 2,
  "query": "approval flows with email notification",
  "method": "llm"
}
```

---

## Cost Breakdown

### Per Search
- **Input**: ~1,500-3,000 tokens (pattern summaries)
- **Output**: ~50-100 tokens (list of IDs)
- **Cost**: $0.001-0.003 per search
- **Cache**: Free on repeat queries (24 hours)

### Daily Limit
- **Hard cap**: $1.00/day
- **Searches**: 300-1,000 searches/day (depending on query)
- **Protection**: Rejects requests after limit hit

### Example: 100 Patterns
- First search: `$0.002`
- Same query again: `$0.00` (cached)
- Different query: `$0.002`

**Total with caching**: $0.02-0.05/day for typical usage

---

## Free Tier vs. Pro Tier

### Free Tier (Current)
- Natural language search available
- User brings their own Anthropic API key
- $1/day limit (their cost, not yours)

### Pro Tier (Future)
- No API key needed (you provide it)
- Higher daily limits ($10/day = 3,000-10,000 searches)
- Priority processing
- **Your revenue**: $99-149/year Pro subscription

**Key insight**: Free tier users pay Anthropic directly (~$0.50-2/month). Pro tier users pay YOU ($12/month), and you pay Anthropic (~$2-5/month). Margin: $7-10/month per Pro user.

---

## Frontend Integration (Next Step)

Add a "Ask AI" button to the search bar:

```html
<!-- In frontend/index.html -->
<div class="search-bar">
  <input type="text" id="search-input" placeholder="Search patterns...">
  <button id="keyword-search">Search</button>
  <button id="ai-search" class="ai-button">🤖 Ask AI</button>
</div>
```

```javascript
// In frontend/js/inventory.js
document.getElementById('ai-search').addEventListener('click', async () => {
  const query = document.getElementById('search-input').value;
  const response = await fetch(`/api/patterns/search/nl?query=${encodeURIComponent(query)}`, {
    method: 'POST'
  });
  const data = await response.json();
  renderPatterns(data.results);
});
```

**UX Flow**:
1. User types: "approval flows with email"
2. Clicks "Ask AI" button
3. 1-2 second wait (show loading spinner)
4. Results appear, sorted by relevance

---

## Monitoring Costs

### Check Daily Spend
```bash
curl http://localhost:8000/api/patterns/search/cost
# Response: {"daily_cost": 0.08, "limit": 1.00}
```

### View Cache Stats
```bash
ls ~/.blackboxaf/llm_cache/
# Shows cached queries (*.json files)
```

### Clear Cache (for testing)
```python
from blackboxaf.api.llm import clear_cache
clear_cache()
```

---

## Troubleshooting

### Error: "LLM features require the 'anthropic' package"
**Fix**: `pip install anthropic`

### Error: "ANTHROPIC_API_KEY environment variable not set"
**Fix**: Set the env var (see Setup step 2)

### Error: "Daily LLM cost limit reached"
**Fix**: Wait until tomorrow, or increase `_MAX_DAILY_COST` in `src/blackboxaf/api/llm.py`

### Slow Responses (3-5 seconds)
**Normal**: First query is slow (API call). Repeat queries are instant (cached).

### Bad Results
**Fix**: The LLM is pattern-matching on names/tags. If patterns have poor names/tags, results suffer. Solution: Better pattern naming during extraction.

---

## Roadmap: More LLM Features

### Next (Week 1-2):
- [ ] Add "Ask AI" button to frontend
- [ ] Show cost estimate before search
- [ ] Display "cached" badge for repeat queries

### Soon (Month 1-3):
- [ ] AI-powered pattern explanations ("What does this flow do?")
- [ ] Pattern recommendations ("Users who viewed this also liked...")
- [ ] Semantic clustering ("Group these 50 flows into families")

### Later (Quarter 2-4):
- [ ] Code generation from patterns
- [ ] Quality scoring with explanations
- [ ] Team chat with pattern library

---

## Marketing Angle

### For Launch Post:
> "BlackBoxAF now has **natural language search** powered by Claude AI. Instead of keyword matching, ask questions like a human:
>
> - 'approval flows with email notification'
> - 'validation rules for email format'
> - 'complex flows with multiple decisions'
>
> Cost: $0.001-0.003 per search. Cached for 24 hours. $1/day limit to prevent runaway costs."

### For Pro Tier Pitch:
> "**Free tier**: Bring your own Anthropic API key (you pay ~$0.50-2/month to Anthropic directly).
>
> **Pro tier ($99/year)**: No API key needed. We provide unlimited AI search, plus AI-powered pattern explanations and recommendations."

---

## Bottom Line

You now have:
- ✅ Natural language search (cost-optimized)
- ✅ r/Salesforce launch post (traffic to site)
- ✅ GitHub README (traffic to site)
- ✅ Logo design (matches site aesthetic)

**Next action**: Add your Anthropic API key, test a search, then add the "Ask AI" button to the frontend.

**Launch timeline**: You're 90% ready. Just need to:
1. Take 5 screenshots
2. Create GitHub repo
3. Post on r/salesforce

Ship it this week. 🚀
