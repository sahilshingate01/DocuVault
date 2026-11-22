# DocuVault Desktop Application - Architecture & User Manual

> **DigiLocker-Grade Secure Document Management Desktop Client**  
> Native macOS, Linux, and Windows desktop environment for tamper-evident document governance, fine-grained clearance controls, and cryptographic provenance.

---

## 🏛️ Desktop Architecture

The DocuVault Desktop application combines an **Electron 33+ native shell** with a **FastAPI backend platform**, communicating via a secure, context-isolated IPC bridge and REST API endpoints.

```
+---------------------------------------------------------------------------------------+
|                               DocuVault Desktop Client                                |
+---------------------------------------------------------------------------------------+
|  [ Electron Main Process ]                                                            |
|    - Application Lifecycle & Window Management                                       |
|    - Automated Backend Lifecycle Manager (spawns & monitors FastAPI)                  |
|    - Native File System Dialogs (Open, Save, Export)                                  |
|    - Native SHA-256 Crypto Engine (Streaming chunked file hashing)                    |
|    - Native Menu Bar & Accelerator Dispatcher (⌘U, ⌘N, ⌘O, ⌘L, ⌘R)                    |
+---------------------------------------------------------------------------------------+
                                           |
                              [ Preload Security Bridge ]
                                (contextBridge.exposeInMainWorld)
                                           |
+---------------------------------------------------------------------------------------+
|  [ Electron Renderer Process (Modern Dark UI) ]                                       |
|    - Live Backend Connection & Health Status Indicator                                |
|    - Live Persona & Clearance Tier Switcher (SP, Judge, SI, Clerk, CEO, Analyst)      |
|    - Secure Workspaces & Cases Explorer (Boundary-enforced multi-tenant cases)         |
|    - Document Vault with SHA-256 Fingerprints & Version Provenance                     |
|    - Offline / Local File Integrity Verifier (Drag-and-Drop Checksum Matcher)           |
|    - DigiLocker Digital Signature Studio (RSA-PSS Cryptographic Non-Repudiation)      |
|    - Tamper-Evident Hash-Chained Audit Ledger Visualizer & Verifier                   |
|    - Clearance-Aware Document Search Engine (Tag, Title, and SHA-256 lookup)          |
|    - Multi-Tenant Organization, Department & Position RBAC Inspector                  |
|    - ABAC Authorization Engine & Security SOC Dashboard                               |
+---------------------------------------------------------------------------------------+
                                           |
                             HTTP / REST (Bearer JWT Auth)
                                           |
+---------------------------------------------------------------------------------------+
|  [ DocuVault REST Backend Engine (127.0.0.1:8000) ]                                   |
|    - SQLite / PostgreSQL Database                                                     |
|    - Cryptographic Storage Vault (vault_storage/)                                     |
+---------------------------------------------------------------------------------------+
```

---

## 🚀 Quick Launch

### 1. Automated Launcher (Recommended)
The launcher verifies Python dependencies, initializes seed data if the database is fresh, installs desktop dependencies if missing, and starts both backend and desktop:
```bash
./run_desktop.sh
```

### 2. NPM Command
From the project root:
```bash
npm run desktop
```

Or for development mode with DevTools enabled:
```bash
npm run desktop:dev
```

### 3. Manual Startup
Run the server and desktop app in separate terminals:
```bash
# Terminal 1: FastAPI Backend
PYTHONPATH=. venv/bin/python3 app/main.py

# Terminal 2: Electron Desktop Client
cd desktop
npm start
```

---

## ⚡ Native Keyboard Shortcuts

| Shortcut (macOS) | Shortcut (Windows/Linux) | Action |
| :--- | :--- | :--- |
| **⌘U** | **Ctrl+U** | Open Secure Document Upload Modal |
| **⌘N** | **Ctrl+N** | Create New Case / Workspace |
| **⌘O** | **Ctrl+O** | Open Offline / Local File Integrity Verifier |
| **⌘L** | **Ctrl+L** | Run Cryptographic Audit Ledger Integrity Verification |
| **⌘R** | **Ctrl+R** | Refresh Vault Data & Ledger State |
| **⌘Q** | **Alt+F4** | Quit Desktop Application |

---

## 🛡️ Core Desktop Capabilities

### 1. Offline / Local File Integrity Verifier
The Desktop app allows users to drag and drop **any file** from their local computer directly into the app (or click **⌘O**). The app:
1. Streams the file from disk through native Node.js cryptography to calculate its exact SHA-256 checksum.
2. Queries the DocuVault ledger to check if the file matches any recorded vault version.
3. Automatically categorizes the file:
   - **Authentic Vault Match**: Exact match with document title, version number, and timestamp.
   - **Tamper Alert**: Filename matches a known case file, but the SHA-256 fingerprint differs (proving the file on disk was modified).
   - **Unregistered**: File is not present in the vault.

### 2. DigiLocker Digital Signature Studio
- Authorized roles (**Superintendent of Police**, **District Judge**, **CEO**) can digitally sign approved document versions.
- Signatures are generated using RSA-PSS-2048 asymmetric keys.
- Signatures can be verified mathematically on-demand.

### 3. Tamper-Evident Hash-Chained Audit Ledger
Every single action (read, upload, download, approve, sign, access denied) is cryptographically linked:
$$\text{EntryHash}_n = \text{SHA-256}(\text{EntryHash}_{n-1} \,\|\, \text{Timestamp} \,\|\, \text{Actor} \,\|\, \text{Action} \,\|\, \text{Resource} \,\|\, \text{Payload})$$
- Click **Verify Ledger Integrity (⌘L)** to mathematically trace the entire chain from Genesis block to latest block.
- Click **Simulate Tampering** to tamper with an entry and observe how the desktop app detects and flags the exact broken block.
- Click **Restore Ledger** to return the chain to pristine condition.
- Click **Export Ledger** to save a forensic JSON record to your computer using native save dialogs.

### 4. Interactive Persona Switcher
Switch between test personas on-the-fly from the top titlebar:
- **SP Vikram Sharma**: Superintendent of Police (`TOP_SECRET` clearance, signing authority)
- **Hon. Judge Sneha Kulkarni**: District Judge (`TOP_SECRET` judicial clearance, signing authority)
- **Sub-Inspector Arjun Das**: Investigating Officer (`CONFIDENTIAL` clearance)
- **Manoj Verma**: Court Record Clerk (`RESTRICTED` clearance)
- **Siddharth Singhania**: Enterprise CEO (`TOP_SECRET` clearance)
- **Riya Sen**: Junior Analyst (`UNCLASSIFIED` clearance)

---

## 🧪 Desktop Test Suite

The desktop app includes automated structure and integration tests under `tests/test_desktop_app.py`:
```bash
PYTHONPATH=. venv/bin/pytest tests/test_desktop_app.py -v
```
Verifies directory structure, package manifests, Node syntax validation, preload API exports, and IPC communication channels.
