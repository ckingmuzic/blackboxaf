# Terms of Use

BlackBoxAF is an open-source tool for extracting reusable structural patterns from Salesforce metadata. By using this software, you agree to the following terms.

## How It Works

BlackBoxAF processes SFDX project files stored on your local machine. It extracts anonymized architectural patterns (flow logic, validation structures, object relationships) and stores them in a local database.

- **Fully offline** — no API calls, no cloud services, no data transmission
- **No credentials required** — works with files you've already pulled via SFDX CLI
- **Anonymization built in** — org-specific identifiers, brand names, and sensitive data are automatically scrubbed

## Your Responsibilities

You are responsible for ensuring you have proper authorization to process any metadata you scan. This includes:

- Obtaining written permission before scanning client org metadata
- Reviewing extracted patterns before sharing externally
- Complying with any applicable NDAs, confidentiality agreements, or employment contracts
- Following all relevant data protection regulations (GDPR, CCPA, etc.)

## Anonymization Notice

BlackBoxAF applies multiple layers of anonymization including regex-based scrubbing, heuristic brand detection, and dictionary-based company name matching. However, **no automated anonymization is guaranteed to be 100% complete**. Always review output before sharing.

## No Warranty

This software is provided "as is" without warranty of any kind. The author makes no guarantees regarding accuracy, completeness of anonymization, or fitness for any particular purpose.

## Limitation of Liability

The author is not liable for any damages arising from the use of this software, including but not limited to data exposure, legal disputes, or breach of third-party agreements.

## Salesforce Trademark Notice

"Salesforce" and related marks are trademarks of Salesforce, Inc. BlackBoxAF is an independent project, not affiliated with or endorsed by Salesforce.

## Governing Law

These terms are governed by the laws of the State of Texas.

## Contact

- Email: C.king@ckingmuzic.com
- GitHub: [github.com/ckingmuzic](https://github.com/ckingmuzic)

---

Last updated: February 2026
