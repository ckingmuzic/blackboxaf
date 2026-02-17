# BlackBoxAF

> **Extract the architecture. Reuse the knowledge.**

BlackBoxAF scans Salesforce SFDX projects and builds a searchable catalog of reusable metadata patterns—fully anonymized, 100% local, zero data leaks.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## Quick Start

### Option 1: Install via pip

```bash
pip install blackboxaf
blackboxaf
```

Opens your browser to `http://localhost:8000`.

### Option 2: Download Windows .exe

No Python needed. Just download, double-click, and run.

👉 **[Download BlackBoxAF.exe](https://github.com/ckingmuzic/blackboxaf/releases)**

---

## What It Does

BlackBoxAF extracts **structural patterns** from Salesforce metadata:
- **Flows**: Decision trees, record operations, screens, loops, subflows
- **Validation Rules**: Formula structures, operator patterns, field references
- **Apex Classes**: Method signatures, SOQL patterns, DML operations
- **LWC Components**: Wire adapters, lifecycle hooks, child component usage
- **Custom Objects & Fields**: Relationships, field types, picklist structures
- **Reports**: Groupings, filters, custom summary formulas
- **Page Layouts**: Sections, related lists, quick actions

### Anonymization Example

**Before** (raw metadata):
```xml
<field>AcmeCloud_Customer_Status__c</field>
<email>jane.doe@client.com</email>
<recordId>001xx000003DGbQAAW</recordId>
```

**After** (anonymized):
```xml
<field>Brand_A_Customer_Status__c</field>
<email>[EMAIL]</email>
<recordId>[SF_ID]</recordId>
```

**Ecosystem products preserved** (Marketo, ZoomInfo, etc.) because they indicate integration requirements—that's transferable structural knowledge.

---

## Why This Matters

Every Salesforce consultant rebuilds the same patterns:
- ✅ 3-tier approval flows with fault handling
- ✅ Validation rules for email/phone format
- ✅ Record-triggered automation
- ✅ Territory assignment logic

**You've built these 10 times.** But they're trapped in past projects, lost in SFDX repos.

BlackBoxAF extracts, anonymizes, and catalogs them—so you never rebuild from scratch again.

---

## Real-World Usage

**Consulting Firm**: Scan all past projects → 5,000+ patterns. Juniors search before building. Seniors' expertise codified. **30% faster implementations.**

**Solo Admin**: Extract anonymized patterns before leaving a role. Legal to keep, valuable for next job. **Career insurance policy.**

**Consultant**: "I need an approval flow with email notification" → search → 12 variations found in 0.02 seconds. **Saves 30-60 minutes per implementation.**

---

## Architecture

```
blackboxaf/
├─ extraction/         # Metadata parsers (7 types)
├─ db/                 # SQLite + FTS5
├─ api/                # FastAPI REST API
├─ frontend/           # Dark-theme web UI
└─ app.py              # Entry point
```

**Security**: Host header validation, CORS restricted to localhost, binds to `127.0.0.1` only.

---

## No Tool Like This Exists

- **Gearset/Salto**: Compare specific orgs. Don't anonymize for cross-org reuse.
- **Code Analyzer**: Find quality issues. Don't capture structural knowledge.
- **Flow Templates**: Hand-crafted examples. Don't mine patterns from real orgs.

**BlackBoxAF fills the gap**: automated pattern extraction with anonymization.

---

## Development

```bash
git clone https://github.com/ckingmuzic/blackboxaf.git
cd blackboxaf
pip install -e ".[dev]"
blackboxaf
```

Build standalone .exe:
```bash
python build_exe.py  # Output: dist/BlackBoxAF.exe
```

---

## Ethics & Legal

**TL;DR**: Extracting architecture = ethical. Stealing client secrets = not.

BlackBoxAF anonymizes structural patterns (flow topology, validation rule structure). But **you're responsible** for:
- Getting client permission before scanning
- Not sharing client-specific competitive advantages
- Complying with NDAs

[Read full ethics guide →](DISCLAIMER.md)

---

## Contributing

Help wanted:
- [ ] New parsers (Territory Rules, Einstein Bots, Dashboards)
- [ ] LLM features (natural language search, code generation)
- [ ] Testing (edge cases, performance benchmarks)

---

## Built By

**C.King** - Salesforce Architect, Consultant, Developer

- 🌐 [ckingmuzic.com](https://ckingmuzic.com) - SFDC Services & Multimedia Productions
- 💼 [LinkedIn](https://linkedin.com/in/cking)
- 🐙 [GitHub](https://github.com/ckingmuzic)

*If BlackBoxAF saves you time:*
- ⭐ **Star this repo** (helps others discover it)
- 💬 **Share on LinkedIn** (tag me!)

---

## License

MIT - Use it for anything. No attribution required. No warranty provided.

---

<div align="center">
  <p><strong>Stop rebuilding. Start reusing.</strong></p>
  <p>⭐ Star if you found this useful!</p>
</div>
