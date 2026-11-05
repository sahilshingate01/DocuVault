# DocuVault - Secure Document Management System

> **DigiLocker-grade backend platform & client for tamper-evident document governance, fine-grained clearance control, and verifiable cryptographic provenance.**

---

## 📌 Problem Statement

Organizations routinely keep highly sensitive documents in unsecured shared drives, email attachments, and paper files. This creates acute vulnerabilities:
- **Absence of Access Control**: Inability to strictly restrict who can view, approve, sign, or modify sensitive materials.
- **Unverifiable File Integrity**: Inability to mathematically prove whether a file or statement has been tampered with or replaced.
- **Missing Audit Accountability**: Unclear visibility into who took what action, when, and from where.
- **Discovery Bottlenecks**: Inefficient retrieval across case files, departments, and clearance zones.

In critical environments such as police departments and judicial courts, an altered witness statement, case diary, or ballistics report can compromise justice. In corporate enterprises, leaked mergers, payroll records, or altered contracts inflict devastating financial and legal damage.

**DocuVault** provides an organization-wide secure vault inspired by the integrity principles of **DigiLocker**. Every document version is fingerprinted with SHA-256, approved versions can be digitally signed using asymmetric cryptography, access is enforced through dynamic department/position/classification matrixes, and all activities are recorded in a **tamper-evident hash-chained audit ledger**.

---

## 🏛 Core Architectural Pillars

```
+-----------------------------------------------------------------------------------+
|                               DocuVault Architecture                              |
+-----------------------------------------------------------------------------------+
|  [ Client Web Dashboard ] <---> [ REST API Gateway (FastAPI / OpenAPI) ]           |
|                                         |                                         |
|                   +---------------------+---------------------+                   |
|                   |                     |                     |                   |
|         [ Access Control Engine ]  [ Crypto Engine ]    [ Audit Ledger Engine ]   |
|         - Org / Department / Pos   - SHA-256 Hasher     - Hash-chained blocks     |
|         - Clearance Levels         - Ed25519/RSA Sign   - Previous Hash Linkage   |
|         - Workspace Boundaries     - Signature Verify   - Tamper Detection        |
|                   |                     |                     |                   |
|                   +---------------------+---------------------+                   |
|                                         |                                         |
|                 [ SQLite / PostgreSQL ] + [ Encrypted Vault Storage ]              |
+-----------------------------------------------------------------------------------+
```

1. **Multi-Tenant Hierarchy & Dynamic Roles**:
   - Each Organization defines its own departments (e.g., Forensic Investigation, Cyber Crime, Criminal Court, Finance).
   - Each Department defines positions (e.g., *Superintendent of Police*, *Investigating Officer*, *Judge*, *Court Clerk*, *CEO*, *Legal Counsel*).
   - Permissions are bound to positions and cleared security tiers.

2. **Workspaces & Classification**:
   - Documents reside in structured Workspaces (representing a *Case*, a *Project*, or an *Inquiry File*).
   - Every document holds a mandatory Security Classification: `UNCLASSIFIED`, `RESTRICTED`, `CONFIDENTIAL`, `SECRET`, or `TOP_SECRET`.
   - On every request, DocuVault validates whether the user's position clearance permits access.

3. **Cryptographic Fingerprinting (SHA-256)**:
   - Every uploaded version is checksummed with SHA-256 at the storage layer.
   - Any bit-level modification immediately invalidates the file integrity check.

4. **Digital Signatures & Approvals**:
   - Approved document versions can be digitally signed by authorized personnel (e.g., Judges, SPs, Department Heads).
   - Signatures are verified mathematically against public keys and tamper-verified on access.

5. **Tamper-Evident Hash-Chained Audit Ledger**:
   - Every action (read, write, approve, sign, access denied) is appended to a cryptographic ledger where:
     $$\text{EntryHash}_n = \text{SHA-256}(\text{EntryHash}_{n-1} \,\|\, \text{Timestamp} \,\|\, \text{Actor} \,\|\, \text{Action} \,\|\, \text{Resource} \,\|\, \text{Payload})$$
   - Any unauthorized modification of the database ledger breaks the cryptographic chain and triggers an instant alert.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- (Optional) Docker & Docker Compose

### Local Setup
```bash
# Clone the repository
git clone https://github.com/sahilshingate01/DocuVault.git
cd DocuVault

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the seed generator (populates Police, Judiciary, and Enterprise test suites)
python3 scripts/seed_data.py

# Launch the server
python3 app/main.py
```

Open your browser to:
- **Interactive Web App**: [http://localhost:8000/](http://localhost:8000/)
- **Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 🧪 Testing the Security Model

Run the comprehensive test suite covering cryptographic validation, audit ledger tampering detection, and clearance violation rejection:

```bash
pytest -v
```
