# DocuVault Architecture & Security Specifications

## 1. System Overview

**DocuVault** is an enterprise-grade secure document management platform modeled after the proven security principles of **DigiLocker**. It solves four critical vulnerabilities in sensitive document pipelines:
1. **Uncontrolled Dissemination**: Access governed by dynamic multi-tiered organization/department/position matrices and security clearance levels.
2. **Silent File Tampering**: Every document version is fingerprinted with SHA-256 at ingest; disk bytes are verified on every download.
3. **Repudiation of Approvals**: Approved document versions can be digitally signed using RSA-PSS asymmetric cryptography.
4. **Audit Log Erasure/Manipulation**: All operations are appended to an immutable, cryptographically hash-chained audit ledger.

---

## 2. Multi-Tenant Authorization & Clearance Matrix

DocuVault enforces a combined **RBAC (Role-Based Access Control)** and **MAC (Mandatory Access Control)** model:

### Security Classification Hierarchy
$$\text{UNCLASSIFIED (1)} < \text{RESTRICTED (2)} < \text{CONFIDENTIAL (3)} < \text{SECRET (4)} < \text{TOP\_SECRET (5)}$$

A user is authorized to read or act upon a document if and only if:
$$\text{Rank}(\text{User Effective Clearance}) \ge \text{Rank}(\text{Document Classification})$$
where:
$$\text{Rank}(\text{User Effective Clearance}) = \min\big(\text{Rank}(\text{User.Clearance}), \text{Rank}(\text{Position.MaxClearance})\big)$$

### Policy Enforcement Evaluation Pipeline
```
[ Incoming Request ]
        │
        ▼
[ Tenant Isolation Check ] ──(Mismatch)──> [ 403 Forbidden + Audit Log ]
        │ (Matches)
        ▼
[ Workspace Clearance Check ] ──(Insufficient)──> [ 403 Forbidden + Audit Log ]
        │ (Satisfied)
        ▼
[ Document Clearance Check ] ──(Insufficient)──> [ 403 Forbidden + Audit Log ]
        │ (Satisfied)
        ▼
[ Position Action Capability ] ──(Missing Action)──> [ 403 Forbidden + Audit Log ]
        │ (Authorized)
        ▼
[ Proceed & Record SUCCESS in Cryptographic Ledger ]
```

---

## 3. Cryptographic Provenance Architecture

### 3.1 Content-Addressed Storage & SHA-256 Fingerprinting
When a document is uploaded:
1. The raw stream is hashed through streaming SHA-256 blocks:
   $$\text{Fingerprint} = \text{SHA-256}(\text{FileBytes})$$
2. The file is placed in content-addressed storage using its fingerprint: `vault_storage/documents/{sha256}_{original_filename}`.
3. On every subsequent retrieval or download, the server recalculates the SHA-256 digest of the file on disk. If the calculated digest differs from `version.sha256_hash`, the download is aborted, and a `TAMPER_DETECTED` security alert is written to the audit ledger.

### 3.2 RSA-PSS Digital Signatures
Approved document versions can be digitally signed by authorized officers:
- Algorithm: **RSA-PSS** (Probabilistic Signature Scheme) with SHA-256 and maximum salt length.
- The signer's private key signs the document's SHA-256 fingerprint:
  $$\sigma = \text{Sign}_{K_{\text{priv}}}(\text{Fingerprint})$$
- Anyone holding the officer's public key $K_{\text{pub}}$ can verify:
  $$\text{Verify}_{K_{\text{pub}}}(\text{Fingerprint}, \sigma) \stackrel{?}{=} \text{True}$$

---

## 4. Tamper-Evident Hash-Chained Audit Ledger

Traditional relational databases allow database administrators or intruders with direct SQL access to alter or delete logs without detection.

DocuVault solves this by chaining every audit record:
- **Genesis Block ($N = 1$)**:
  $$\text{PrevHash}_1 = 0000000000000000000000000000000000000000000000000000000000000000$$
- **Chained Block ($N > 1$)**:
  $$\text{PrevHash}_N = \text{EntryHash}_{N-1}$$
- **Canonical Hash Generation**:
  $$\text{EntryHash}_N = \text{SHA-256}\big(N \,\|\, \text{TimestampISO} \,\|\, \text{PrevHash}_N \,\|\, \text{UserID} \,\|\, \text{Action} \,\|\, \text{ResourceType} \,\|\, \text{ResourceID} \,\|\, \text{Status} \,\|\, \text{DetailsJSON}\big)$$

### Mathematical Verification Procedure
$$\text{AuditService.verify\_ledger\_integrity()}$$
Iterates through all blocks from $N=1$ to tip:
1. Verifies $N_{i+1} = N_i + 1$ (Sequence Continuity).
2. Verifies $\text{PrevHash}_{i+1} = \text{EntryHash}_i$ (Hash Chain Linkage).
3. Recomputes $\text{EntryHash}_i$ over the canonical fields.
Any alteration of a past record immediately breaks all subsequent block hashes and flags the exact corrupted block number.
