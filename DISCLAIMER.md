# Legal Disclaimer & Terms of Use

## NO WARRANTY

BlackBoxAF is provided "as is" without warranty of any kind, express or implied. The author makes no warranties regarding:
- Accuracy of extracted patterns
- Completeness of anonymization
- Fitness for any particular purpose
- Compatibility with any Salesforce org or API version

**USE AT YOUR OWN RISK.**

---

## Data Processing & Privacy

### What BlackBoxAF Does
- Scans local SFDX project directories (XML metadata files)
- Extracts structural patterns (flow logic, validation formulas, object relationships)
- Anonymizes org-specific data (IDs, emails, URLs, business brand names)
- Stores patterns in a local SQLite database

### What BlackBoxAF Does NOT Do
- **Does not connect to Salesforce orgs** - no API calls, no authentication
- **Does not transmit data** - all processing is 100% local
- **Does not store credentials** - works with files you've already retrieved via SFDX CLI
- **Does not guarantee perfect anonymization** - review extracted patterns before sharing

### Your Responsibilities
1. **Obtain proper authorization** before scanning client org metadata
2. **Review extracted patterns** for sensitive data before sharing with third parties
3. **Comply with all applicable laws** including GDPR, CCPA, and contractual obligations
4. **Respect Salesforce terms of service** and client confidentiality agreements

---

## Intellectual Property & Ethical Use

### Client Metadata
- Metadata from client Salesforce orgs may be subject to **confidentiality agreements**
- Structural patterns (e.g., "approval flow with 3-tier decision tree") are generally **not proprietary**
- Business-specific logic (e.g., "discount rules for ABC Corp's pricing model") may be **confidential**

**You are responsible for determining what can legally be extracted and reused.**

### Salesforce Trademarks
- "Salesforce" and related trademarks are owned by Salesforce, Inc.
- BlackBoxAF is an independent tool, not affiliated with or endorsed by Salesforce

### Fair Use Doctrine
- Extracting structural patterns for learning, reference, or inspiration is generally considered **transformative fair use**
- Copying entire implementations verbatim may violate client agreements or copyright

**Consult legal counsel if you have concerns about specific use cases.**

---

## Limitation of Liability

To the maximum extent permitted by law:

1. **No liability for damages** - The author is not liable for any direct, indirect, incidental, or consequential damages arising from use of BlackBoxAF

2. **No liability for data breaches** - You are responsible for securing extracted patterns and complying with data protection laws

3. **No liability for legal disputes** - If you face legal action related to metadata extraction, the author is not responsible

4. **No professional advice** - This tool does not constitute legal, accounting, or professional advice

---

## Acceptable Use Policy

### ✅ PERMITTED USES
- Extracting patterns from your own Salesforce orgs
- Extracting patterns from client orgs **with written authorization**
- Building a personal reference library of architectural patterns
- Using patterns as inspiration for new implementations
- Sharing anonymized patterns in educational contexts (blog posts, training materials)

### ❌ PROHIBITED USES
- Extracting metadata without authorization
- Sharing client-specific business logic without permission
- Violating non-disclosure agreements (NDAs) or confidentiality clauses
- Circumventing Salesforce security controls
- Using BlackBoxAF for competitive intelligence gathering without consent

---

## Compliance with Laws

Users must comply with all applicable laws, including but not limited to:

### Data Protection
- **GDPR** (EU General Data Protection Regulation)
- **CCPA** (California Consumer Privacy Act)
- **PIPEDA** (Canada Personal Information Protection)

### Intellectual Property
- Copyright laws in your jurisdiction
- Trade secret protections
- Patent laws (if applicable to extracted logic)

### Contractual
- Salesforce Master Subscription Agreement
- Client services agreements
- Employment contracts (if extracting from employer-owned orgs)

---

## Indemnification

By using BlackBoxAF, you agree to indemnify and hold harmless the author from any claims, damages, or legal fees arising from:
- Your misuse of the software
- Violation of third-party rights
- Breach of confidentiality agreements
- Non-compliance with applicable laws

---

## Governing Law

This disclaimer is governed by the laws of the State of Texas, without regard to conflict of law principles.

---

## Contact

For questions about appropriate use or legal concerns:
- Email: C.king@ckingmuzic.com
- GitHub: github.com/ckingmuzic

---

**Last Updated**: February 2026

**By using BlackBoxAF, you acknowledge that you have read, understood, and agree to be bound by this disclaimer.**
