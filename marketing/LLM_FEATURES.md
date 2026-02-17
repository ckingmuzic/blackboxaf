# LLM-Optimized Features for BlackBoxAF

## Current State vs. LLM-Enhanced Future

| Feature | Current (v0.1) | With LLM Enhancement |
|---------|---------------|---------------------|
| **Search** | Keyword match (FTS5) | Natural language: "Find approval flows with email notifications" |
| **Pattern Discovery** | Browse/filter manually | AI suggests: "Users who viewed this pattern also used..." |
| **Pattern Comparison** | Side-by-side manual review | AI highlights: "These 3 flows differ only in email recipient logic" |
| **Code Generation** | Copy-paste structure manually | AI generates: "Create a flow like Pattern #42 for Opportunity object" |
| **Documentation** | Raw field references | AI explains: "This flow creates a Task when Opportunity Stage = Closed Won" |

---

## LLM Feature Roadmap

### Phase 1: Search & Discovery (Easiest, Highest Value)

#### 1. Natural Language Search
**Current**: User searches "decision" → finds all patterns with "decision" in name/tags
**LLM-Enhanced**: User asks "approval flows with multiple decision branches" → AI understands intent

**Implementation**:
```python
# Add to patterns.py API
@router.post("/api/patterns/nl-search")
async def nl_search(query: str):
    # Send to Claude API with pattern catalog context
    prompt = f"""
    User query: {query}

    Available patterns (sample):
    - Flow: 3-Tier Approval with Fault Handling (complexity: 4, tags: approval, decision, fault)
    - Flow: Lead Assignment by Territory (complexity: 2, tags: assignment, record-lookup)
    - Validation: Email Format Check (complexity: 1, tags: email, regex, format)

    Which patterns best match the user's intent? Return pattern IDs.
    """
    # Parse AI response, return matching patterns
```

**Value**: "Find what I need, even if I don't know the exact keywords"

---

#### 2. Pattern Recommendations
**Feature**: "Consultants who extracted this approval flow also extracted these validation rules"

**Implementation**:
- Track which patterns are extracted together (co-occurrence matrix)
- Use Claude to analyze: "Why do these patterns go together?"
- Surface recommendations in UI: "Commonly paired with..."

**Value**: Pattern discovery (users find related patterns they didn't know to search for)

---

#### 3. Semantic Clustering
**Feature**: Auto-group similar patterns into "pattern families"

**Example**:
```
📁 Approval Flow Patterns (12)
  ├─ Simple 1-Tier (3 patterns)
  ├─ Multi-Tier with Escalation (5 patterns)
  └─ Dynamic Approver Selection (4 patterns)
```

**Implementation**:
- Use Claude to analyze pattern structures: "What makes these 12 approval flows similar/different?"
- Generate taxonomy of pattern types
- Display as a navigable tree in UI

**Value**: Browse by architectural similarity, not just keywords

---

### Phase 2: Code Generation (Medium Difficulty, High Wow Factor)

#### 4. Pattern-to-Code Generator
**Feature**: "Generate a flow like Pattern #42, but for Contact object instead of Lead"

**User Flow**:
1. User finds a pattern: "Opportunity Approval Flow"
2. Clicks "Generate for different object"
3. AI prompts: "Which object? Which fields map to Stage/OwnerId/Amount?"
4. AI generates new flow XML with field mappings applied

**Implementation**:
```python
# New API endpoint
@router.post("/api/patterns/{id}/generate")
async def generate_variant(
    id: int,
    target_object: str,
    field_mappings: dict[str, str]
):
    pattern = get_pattern(id)

    prompt = f"""
    Generate a Salesforce Flow XML similar to this pattern:
    {pattern.structure}

    But for object: {target_object}
    With field mappings: {field_mappings}

    Preserve the decision logic structure, update field references.
    """

    generated_xml = call_claude_api(prompt)
    return {"xml": generated_xml, "instructions": "..."}
```

**Value**: "I found the pattern. Now make it work for my use case." (Saves 30-60 minutes per adaptation)

---

#### 5. Explain This Pattern (Plain English)
**Feature**: AI-generated plain-English description of what a pattern does

**Example**:
```
Pattern: Opportunity_Stage_Update_Flow

AI Explanation:
"This flow triggers when an Opportunity record is created or updated.
It checks if the Stage field changed to 'Closed Won'. If yes, it:
1. Creates a Task assigned to the Account Owner
2. Updates the Account's Last_Win_Date__c field
3. Sends an email to the Opportunity Owner

The flow includes fault handling: if the Task creation fails,
it logs an error and continues processing."
```

**Implementation**: Pass pattern structure to Claude with prompt: "Explain what this flow does in plain English"

**Value**: Understand complex patterns at a glance (great for learning)

---

### Phase 3: Advanced Analysis (Hard, Differentiator)

#### 6. Pattern Complexity Scoring (AI-Enhanced)
**Current**: Rule-based scoring (decisions=3pts, loops=3pts, etc.)
**LLM-Enhanced**: AI analyzes: "This flow is complex because..."

**Features**:
- **Complexity explanation**: "4/5 complexity due to nested decision logic and fault paths"
- **Simplification suggestions**: "Consider splitting into subflows"
- **Best practices check**: "This flow lacks fault handling on API callouts"

**Value**: Learn from the AI what makes patterns good/bad

---

#### 7. Diff & Merge Patterns
**Feature**: "Show me how Pattern A and Pattern B differ"

**Example**:
```
Pattern A: Approval Flow for Sales
Pattern B: Approval Flow for Service

AI Analysis:
- Both use 3-tier approval structure
- Pattern A includes budget check decision (Amount > $50K)
- Pattern B includes SLA check decision (Priority = High)
- Opportunity to merge into one flow with configurable decision criteria
```

**Value**: Consolidate redundant patterns, identify reusable components

---

#### 8. Pattern Quality Scoring
**Feature**: AI rates pattern quality (maintainability, best practices, documentation)

**Criteria**:
- ✅ Has fault handling
- ✅ Uses subflows for reusable logic
- ⚠️  No description/documentation
- ❌ Uses hardcoded IDs in formulas

**Value**: Learn what "good" looks like (educational)

---

### Phase 4: Team Collaboration (Advanced)

#### 9. Pattern Chat
**Feature**: Ask questions about a pattern

**Example**:
```
User: "Why does this flow use a Loop instead of Get Records?"

AI: "The Loop processes records one-at-a-time to avoid governor limits.
With Get Records, if there are 500+ results, the flow would fail.
The Loop + DML inside is a common pattern for large data volumes."
```

**Value**: On-demand mentorship (especially valuable for junior consultants)

---

#### 10. Team Pattern Recommendations
**Feature**: "Based on our team's past projects, suggest patterns for this new engagement"

**Implementation**:
- Analyze client intake form: "Industry: Healthcare, Use Case: Patient referral tracking"
- Query team library: Which patterns were used for similar projects?
- AI suggests: "Consider these 5 patterns (approval flow, validation rules, report template)"

**Value**: Institutional knowledge codified and surfaced automatically

---

## Implementation Priority

### Quick Wins (Week 1-2):
1. ✅ **Natural Language Search** - Easiest to implement, high user value
2. ✅ **Pattern Explanations** - One API call per pattern, cache results

### Medium-Term (Month 1-3):
3. **Code Generation** - Requires prompt engineering + XML manipulation
4. **Semantic Clustering** - Run once on catalog, update incrementally

### Long-Term (Quarter 2-4):
5. **Quality Scoring** - Need to define good heuristics + train on examples
6. **Pattern Chat** - Requires vector embeddings + RAG setup
7. **Team Features** - Needs multi-user architecture

---

## Technical Architecture for LLM Features

### Option A: Direct Claude API Integration (Recommended)
```python
# config.py
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# api/llm.py
from anthropic import Anthropic

client = Anthropic(api_key=ANTHROPIC_API_KEY)

async def search_patterns_nl(query: str, all_patterns: list):
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"Find patterns matching: {query}\n\nPatterns:\n{pattern_summaries}"
        }]
    )
    return parse_response(response)
```

**Cost**: ~$0.003 per search (Claude 3.5 Sonnet)
**Latency**: 1-3 seconds
**Value**: High-quality results, no training needed

---

### Option B: Local Embeddings (For Offline Use)
```python
# Use sentence-transformers for pattern embeddings
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

# Embed patterns on ingest
pattern_embedding = model.encode(pattern.description)

# Search via cosine similarity
query_embedding = model.encode(user_query)
similar_patterns = find_top_k(query_embedding, pattern_embeddings)
```

**Cost**: Free (local inference)
**Latency**: <100ms
**Trade-off**: Lower quality than Claude API, but works offline

---

### Option C: Hybrid (Best of Both)
- Use local embeddings for fast search/filtering
- Use Claude API for explanations/generation (when user explicitly requests)
- Cache Claude responses to minimize API costs

---

## Revenue Impact of LLM Features

### Free Tier (Current):
- Basic keyword search
- Manual pattern browsing

### Pro Tier ($149/year):
- ✅ Natural language search
- ✅ Pattern explanations (AI-generated)
- ✅ "Similar patterns" recommendations

### Team Tier ($499/year):
- ✅ Code generation from patterns
- ✅ Pattern quality scoring
- ✅ Team chat with pattern library

### Enterprise Tier ($5K+/year):
- ✅ Custom AI training on their pattern library
- ✅ Private Claude API deployment
- ✅ Advanced analytics & recommendations

**Key Insight**: LLM features are a **natural upsell path**. Free users get hooked on basic extraction, paid users get AI superpowers.

---

## Privacy & LLM Considerations

### User Concern: "Is my data sent to Anthropic?"
**Answer**:
- ✅ Patterns are **already anonymized** by BlackBoxAF before any LLM call
- ✅ Only pattern **structure** (not raw org data) is sent to Claude API
- ✅ Anthropic **does not train on API data** (per their terms)
- ✅ Users can opt out of LLM features (use local-only mode)

### Compliance:
- Add to DISCLAIMER.md: "LLM features send anonymized pattern data to Anthropic"
- Provide toggle in UI: "Enable AI features? (Requires internet, sends anonymized data to Claude API)"

---

## Next Steps

### To Add LLM Features (Basic):
1. Get Anthropic API key: https://console.anthropic.com/
2. Add to `config.py`: `ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")`
3. Create `src/blackboxaf/api/llm.py` with search endpoint
4. Update frontend to show "Ask AI" button on search page

### To Test Value:
1. Manually try Claude API on your pattern catalog (paste a few patterns, ask questions)
2. If responses are good → build API integration
3. If responses are meh → tweak prompts or stick with keyword search

---

## Bottom Line

LLM features turn BlackBoxAF from a **catalog** into an **intelligent assistant**.

- **Without LLM**: "Here's a library of 3,000 patterns. Good luck finding what you need."
- **With LLM**: "I found 5 patterns that match your approval flow use case. Here's how they differ. Want me to generate one for Contact object?"

That's the difference between a **tool** and a **10x force multiplier**.

And it's a natural **freemium upsell**: "Try search for free. Unlock AI generation for $149/year."
