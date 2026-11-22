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

## 🖥️ Native Desktop Application

DocuVault features a fully working, native desktop application (powered by Electron) that integrates directly with the backend platform, local filesystem, and cryptographic subsystems.

### Key Desktop Features
- **Auto Backend Management**: The desktop client checks if the DocuVault server is running; if not, it automatically spawns and monitors the FastAPI backend process and terminates it cleanly upon exit.
- **Offline / Local File Integrity Verifier**: Drag and drop any file from your local computer (or press `⌘O`) to calculate its SHA-256 fingerprint on-the-fly and verify whether it matches a registered vault record or has been tampered with.
- **DigiLocker Digital Signature Studio**: One-click RSA-PSS digital signing for authorized positions (Superintendent of Police, District Judge, CEO) and signature verification.
- **Tamper-Evident Ledger Explorer**: Real-time hash-chain visualization, one-click mathematical integrity audits (`⌘L`), tamper simulation, and JSON export.
- **Native Keyboard Shortcuts**:
  - `⌘U` / `Ctrl+U`: Secure document upload
  - `⌘N` / `Ctrl+N`: Create secure workspace
  - `⌘O` / `Ctrl+O`: Local file integrity verifier
  - `⌘L` / `Ctrl+L`: Verify cryptographic audit ledger
  - `⌘R` / `Ctrl+R`: Refresh vault state

### Launching the Desktop Application
```bash
# Option 1: Using the automated launcher script (verifies dependencies and seeds DB if needed)
./run_desktop.sh

# Option 2: Using npm from project root
npm run desktop

# Option 3: Starting backend and desktop separately
PYTHONPATH=. venv/bin/python3 app/main.py  # Terminal 1
cd desktop && npm start                   # Terminal 2
```

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

Run the comprehensive test suite covering cryptographic validation, audit ledger tampering detection, ABAC evaluation, and clearance violation rejection:

```bash
PYTHONPATH=. pytest -v
```

---

## 👥 Module Implementation & Division Summary

### Person 1 – Authentication & Organisation Management (Identity Management)
- **User Registration & Login**: Multi-tenant onboarding, cryptographic keypair generation, credential authentication.
- **JWT Authentication & Refresh Tokens**: Dual token architecture (`/auth/login`, `/auth/refresh`, `/auth/logout`) with token rotation and revocation.
- **Account Security & Lockout**: Salting and bcrypt hashing, password complexity verification, 5-strike brute-force lockout with cooldown timer.
- **Organisation Management**: Complete multi-tenant CRUD (`/api/v1/organizations`) with resource telemetry.
- **Department Management**: Sub-organizational boundaries (`/api/v1/departments`) with head/code indexing.
- **Custom Positions & Designations**: Standard designations (`SP`, `Judge`, `CEO`, `Manager`, `Employee`) and custom positions (`/api/v1/positions`) with capability flags (`can_sign`, `can_approve`, `can_export`, `can_manage_users`) and allowed actions list.
- **User Administration & Role Assignment**: (`/api/v1/users`) assigning users to organizations, departments, positions, and adjusting clearance tiers.

### Person 2 – Document Vault & Version Management (Document Vault)
- **Secure File Storage**: Path traversal defense, executable file upload rejection, atomic streaming upload to temporary files.
- **Document Upload & Download**: APIs (`/api/v1/documents/upload`, `/api/v1/documents/{id}/download`, `/api/v1/documents/{id}/versions/{v}/download`) returning `X-Vault-SHA256` headers.
- **Metadata Management**: Document updating (`PUT /api/v1/documents/{id}`), tagging, search indexing.
- **Workspace Management**: Cases, Projects, Files (`/api/v1/workspaces`) with classification bounds and statistics.
- **Classification Lifecycle**: Bell-LaPadula clearance tiers (`UNCLASSIFIED`, `RESTRICTED`, `CONFIDENTIAL`, `SECRET`, `TOP_SECRET`) with formal reclassification (`POST /documents/{id}/reclassify`).
- **Version Control & Rollback**: Immutable version ledger, version history (`GET /documents/{id}/versions`), and zero-loss version rollback (`POST /documents/{id}/versions/{v}/restore`).
- **File Integrity Verification**: On-demand disk bitstream verification per version (`GET .../verify`) and document-wide (`GET /documents/{id}/verify`).
- **Digital Signatures**: RSA-PSS-SHA256 signing, multi-party signature querying (`/signatures/document/{id}`), verification (`/signatures/verify/{id}`), and signature revocation.
- **Archival & Trash Bin**: Document sealing (`/archive`, `/unarchive`), retention periods, soft deletion to trash bin, and trash restoration.
- **Nexus CLI Client**: Terminal interface for DocuVault operations under `nexus_cli/`.

### Person 3 – Authorization, Security & Audit Management (Security & Audit)
- **Attribute-Based Access Control (ABAC)**: Multi-attribute engine evaluating Subject, Resource, Action, and Context attributes.
- **Position & Department Enforcement**: Action rights mapped to positions, department isolation with executive bypass (SP, Judge, CEO).
- **Bell-LaPadula Multilevel Security**: Simple Security Property (No Read Up) and Confinement Star-Property (No Write Down).
- **Delegated Temporary Clearances**: Time-bound elevated access (`/clearance/grant`, `/clearance/active`, `/clearance/{id}/revoke`).
- **Permission Evaluation Engine**: Real-time pre-flight check API (`POST /security/evaluate`) returning rule traces and decisions.
- **Tamper-Evident Audit Logging**: Cryptographically hash-chained SHA-256 blocks linking every single system event.
- **Document Provenance Trail**: Per-document audit trail (`GET /audit/documents/{id}`) and per-actor audit query (`GET /audit/actors/{id}`).
- **Audit Export**: Forensic export to CSV and JSON formats (`GET /audit/export`).
- **Security Event Monitoring & SOC Dashboard**: Real-time anomaly detection, repeated violation alerts, and security metrics (`/security/dashboard`, `/security/alerts`).
