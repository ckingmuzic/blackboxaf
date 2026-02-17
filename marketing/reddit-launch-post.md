# r/Salesforce Launch Post

---

**Title**: I built a tool to extract and catalog reusable Salesforce patterns (flows, validation rules, Apex, etc.) - and it's free

---

**Post Body**:

Hey r/salesforce,

I'm a SF consultant who got tired of rebuilding the same approval flows, validation rules, and data models on every project. So I built **BlackBoxAF** - a tool that extracts structural patterns from SFDX projects and builds a searchable catalog.

**What it does:**
- Scans local SFDX project directories (no API calls, 100% local)
- Extracts patterns from 7 metadata types: Flows, Validation Rules, Apex, LWC, Reports, Layouts, Objects/Fields
- Automatically anonymizes all org-specific data (business names → "Brand_A", record IDs stripped, etc.)
- Stores patterns in a local SQLite database with full-text search
- Gamified dark-theme web UI (think Minecraft inventory for Salesforce patterns)

**Why I built it:**
Every consultant knows this pain: you build a brilliant 3-tier approval flow with fault handling for Client A. Six months later, Client B needs almost the same thing. You either rebuild from memory (slow) or dig through old repos (messy).

BlackBoxAF lets you extract once, search forever. It's like having a personal pattern library that grows with every engagement.

**Example use case:**
I scanned 21 SFDX projects (~193K files) from past clients. Extracted 3,497 patterns in 2 minutes. Now when I need an approval flow, I search "decision approval email" and get 12 variations to adapt from. Saves me 30-60 minutes per implementation.

**Security/privacy concerns addressed:**
- All processing is local (no cloud uploads)
- Auto-anonymization strips business names (CamelCase detection algorithm)
- Ecosystem products (Marketo, ZoomInfo, etc.) are preserved since they indicate integration requirements
- Zero leaks in my testing (details in the README)

**No tool like this exists:**
I researched the entire SF ecosystem. Gearset/Salto compare specific orgs. Code analyzers check quality. Flow templates are hand-crafted. Nothing extracts reusable structural patterns with anonymization. This is a blue ocean.

**How to use it:**
```bash
# Option 1: Python (if you have it)
pip install blackboxaf
blackboxaf

# Option 2: Windows .exe (no Python needed)
Download from GitHub releases
```

Opens your browser to localhost:8000 with the UI. Point it at your SFDX projects, let it scan, then search/browse patterns.

**It's open source (MIT license):** No paid tiers yet. Just wanted to share something I wish existed when I started consulting.

**Links:**
- GitHub: [https://github.com/YOUR_USERNAME/blackboxaf]
- My site: [https://ckingmuzic.com] (I'm C.King - SF consultant + developer)
- Demo video: [YouTube link when you make it]

**Questions I expect:**
- *"Is this ethical?"* - Yes. Extracting architecture (not client secrets) is standard consultant practice. See the ETHICS_GUIDE.md in the repo.
- *"Will this work on my org?"* - If you have SFDX CLI installed and can retrieve metadata, yes. Works with any SF org/version.
- *"Can I contribute?"* - Absolutely. I'd love help adding parsers for Territories, Einstein Bots, or other metadata types.

**Feedback welcome.** This is v0.1 - I'm sure there are edge cases I haven't hit. If you try it, let me know what breaks or what features you'd want.

Also happy to answer questions about the anonymization algorithm, parser implementation, or why I chose a dark theme (because admins deserve better UX than gray-on-white Setup).

---

**P.S.** If you're at Dreamforce 2026, find me. I'll demo it live and buy you a beer.

---

[End of post]
