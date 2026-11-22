# DocuVault DBMS Major Project Viva — Complete 10-Minute Video Recording Script & Teleprompter

> **Evaluation Submission Details**:
> - **Deadline**: 22nd November 2026
> - **Maximum Duration**: Strictly under 10 minutes (Target: ~8 minutes 45 seconds)
> - **Submission Form**: [Google Form Submission Link](https://docs.google.com/forms/d/e/1FAIpQLSdo3uWnx-u5kdX7iegqCnvTd1TCADkRZMqGKrK6Ld3U4QSATQ/viewform?usp=header)
> - **Evaluation Criteria**: Screen visible throughout recording, real code, database console, live query outputs, constraint rejection for extra credit.

---

## 🎬 Pre-Recording Setup (2 Minutes to Prepare)

1. **Screen Layout (Split-Screen Recommended)**:
   - **Left Half**: DocuVault Application (Desktop App via `./run_desktop.sh` OR Web Browser at `http://127.0.0.1:8000`), opened to the **"🗄️ DBMS Viva Studio"** tab.
   - **Right Half**: Terminal terminal running `./run_viva_console.sh` OR VS Code showing the database models in `app/models/` and `app/services/dbms_service.py`.
2. **Launch Services**:
   ```bash
   # In terminal 1 (starts backend server if not running):
   venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

   # In terminal 2 (launches Desktop app):
   ./run_desktop.sh

   # In terminal 3 (ready for live CLI demo):
   ./run_viva_console.sh --all
   ```
3. **Screen Recorder**: Use OBS Studio, QuickTime Player (Cmd+Shift+5 on Mac), or Loom. Ensure microphone audio is clear and full screen is recorded.

---

## 🎙️ Timed Spoken Transcript (Line-by-Line with Visual Cues)

---

### [0:00 – 0:45] INTRODUCTION & REAL-WORLD PROBLEM CONTEXT
**Visual Cue**: *Show DocuVault main screen with Cobalt theme, then navigate to "🗄️ DBMS Viva Studio".*

> **Spoken**:
> "Hello professors and evaluators. My name is [Your Name], and this is my individual video presentation for the Data Engineering Major Project DBMS Viva.
> 
> My project is **DocuVault**, a secure, DigiLocker-grade document management and cryptographic provenance system. 
> 
> In real-world institutions like police stations, courts, and corporate enterprises, sensitive documents are often stored in unverified shared drives or email attachments. In a criminal trial or court proceeding, a tampered statement can alter a verdict; in an enterprise, a leaked contract causes irreparable harm. 
> 
> DocuVault solves this by combining multi-level clearance access control with SHA-256 fingerprinting, RSA-PSS digital signatures, and an immutable, hash-chained audit ledger. 
> 
> Today, I will walk you through our complete database engineering architecture across all five evaluation questions, demonstrating live queries, schema models, transactions, and a live constraint rejection on screen."

---

### [0:45 – 2:15] QUESTION 1: WHY DID YOU CHOOSE THIS DATABASE?
**Visual Cue**: *Point to Card 1 in DBMS Viva Studio and the Relational Table Inventory table, or run `./run_viva_console.sh --q1` in the terminal.*

> **Spoken**:
> "Addressing Question 1: **Why did we choose this database?**
> 
> For DocuVault, we chose a **Relational Database Management System (RDBMS)**. Specifically, our implementation utilizes **SQLite 3.x with Write-Ahead Logging (WAL mode)** for edge and local vault deployments, and **PostgreSQL** for our multi-tier enterprise configurations, managed via SQLAlchemy ORM.
> 
> **Data Nature**: Our data is highly structured, strongly typed, and deeply relational. As you can see on screen in our table inventory, our data forms a strict multi-tenant governance hierarchy: Organizations contain Departments, Departments define Positions, Positions govern Users, Users operate within Workspaces, and Workspaces contain Documents, Document Versions, Signatures, and Audit Logs.
> 
> **Workload Access Patterns**: Our workload is read-heavy, approximately **80% reads and 20% writes**. 
> - Reads consist of high-frequency Bell-LaPadula clearance checks, document verification against SHA-256 hashes, and case dossier queries.
> - Writes are mission-critical atomic blocks: uploading versioned files, recording cryptographic signatures, and appending immutable audit blocks. We expect to scale to over 100,000 case dossiers and millions of audit links.
> 
> **Consistency Requirements**: We require **Immediate Strong Consistency** with strict ACID transactions. In a legal evidence chain or classified document vault, eventual consistency is completely unacceptable. If an officer's security clearance is revoked, or a document is placed under a judicial gag order, that restriction must take effect immediately across all transactions with zero replication lag or dirty reads.
> 
> **Alternative Considered and Rejected**: We evaluated **MongoDB** and document stores, but rejected them. MongoDB lacks native relational foreign key cascading and cannot enforce strict multi-table referential integrity across decoupled collections. More importantly, maintaining a mathematically tamper-evident, monotonically increasing SHA-256 hash chain in a document database risks split-brain sequencing or orphan documents during network partitions without heavy, distributed two-phase commits."

---

### [2:15 – 4:00] QUESTION 2: SCHEMA ARCHITECTURE & RELATIONAL WALKTHROUGH
**Visual Cue**: *Click the button **"▶ Run 6-Table JOIN"** in DBMS Viva Studio or run `./run_viva_console.sh --q2` in the terminal. Show the resulting output table.*

> **Spoken**:
> "Moving to Question 2: **Walkthrough of our Schema and Data Model.**
> 
> Our relational database consists of **11 normalized tables**. Let's review the core entities and their relationships:
> 
> 1. `organizations`, `departments`, and `positions`: Establish organizational boundaries and RBAC authorities.
> 2. `users`: Stores user identity, hashed passwords, public cryptographic keys, and individual security clearance levels.
> 3. `workspaces`: Represents case containers (such as FIR case files, corporate mergers, or judicial hearings) with a mandatory clearance classification.
> 4. `documents` and `document_versions`: Represents the governed file records. A Document has a 1-to-N relationship with DocumentVersions, storing the exact SHA-256 cryptographic digest, file size, and upload provenance.
> 5. `audit_logs`: The immutable ledger where each entry is cryptographically chained to the previous entry's SHA-256 hash.
> 
> **Cardinality and Relationship Resolutions**:
> - We have standard **1:N** relationships: One Department has many Positions; One Workspace has many Documents; One Document has many Versions.
> - **M:N Relationship Resolution**: 
>   - The Many-to-Many relationship between **Users** and **DocumentVersions** is resolved through our **`digital_signatures`** associative entity, which links signers to specific file versions with RSA-PSS-2048 cryptographic non-repudiation, and through **`chain_of_custody`** for legal evidence transfers.
>   - Similarly, Many-to-Many delegated access between Users and Workspaces is resolved via **`temporary_clearances`**.
> - **Referential Integrity**: We strictly use `ON DELETE CASCADE` for parent-child dependencies so versions and signatures are cleaned up if a case is expunged, and `ON DELETE SET NULL` on user references so historical audit trails are preserved even if an officer leaves the force.
> 
> Let's look at the screen: I am now running our **6-Table Relational JOIN query**. 
> As you can see in the live console output, this single SQL statement joins `documents`, `workspaces`, `organizations`, `departments`, `document_versions`, `users`, `positions`, and `digital_signatures`. In a single query, we see the case number, document classification, SHA-256 hash, the officer who uploaded it, their authorized rank, and the validity of their digital signature."

---

### [4:00 – 5:30] QUESTION 3: NORMAL FORMS (3NF/BCNF) & DELIBERATE DENORMALIZATION
**Visual Cue**: *Point to Card 3 in DBMS Studio or run `./run_viva_console.sh --q3` in the terminal.*

> **Spoken**:
> "Now addressing Question 3: **What Normal Form is our design in, and where did we deliberately break it?**
> 
> Our relational design reaches **Third Normal Form (3NF) and Boyce-Codd Normal Form (BCNF)** across all primary entities.
> 
> Here is our step-by-step normalization decomposition:
> - **First Normal Form (1NF)**: Every table has a distinct primary key using surrogate UUIDs. All attribute values are strictly atomic with no repeating groups. Multi-valued tags or allowed actions are serialized via scalar properties or mapped through junction tables.
> - **Second Normal Form (2NF)**: 1NF is satisfied, and because all tables use single-column surrogate primary keys, there are zero partial key functional dependencies. Every non-key attribute is fully functionally dependent on the entire primary key.
> - **Third Normal Form (3NF)**: 2NF is satisfied, and we eliminated all transitive dependencies of the form $X \to Y \to Z$. For example, the `users` table does not store Department Name or Position Title. It stores only foreign keys `department_id` and `position_id`, preventing update and deletion anomalies.
> - **Functional Dependencies in `documents`**:
>   - `id -> {title, document_number, classification, status, workspace_id, created_by_id}`
>   - `document_number -> {id, title, classification, workspace_id}`
>   Since every determinant is a candidate key, the table strictly satisfies **BCNF**.
> 
> **Where Did We Deliberately Denormalize?**
> We deliberately introduced controlled denormalization in our **`audit_logs`** table.
> Alongside the foreign key `user_id`, we store redundant snapshot columns: `user_email`, `user_name`, and `user_position`. 
> 
> **Why?** Because in a legal court or forensic inquiry conducted five years later, if an employee resigns, changes positions, or is deleted from the `users` table, a dynamic join to `user_id` would either return NULL or show their new position, thereby tampering with historical truth! 
> By taking an immutable identity snapshot at the second of signing, our audit log preserves historical non-repudiation.
> 
> **How is correctness maintained?** The `audit_logs` table is strictly append-only. The snapshot is captured in the transaction pipeline and sealed inside the SHA-256 hash chain, guaranteeing it can never become desynchronized or altered."

---

### [5:30 – 7:15] QUESTION 4: DATA CORRECTNESS, CONSTRAINTS & ATOMIC TRANSACTIONS
**Visual Cue**: *Click **"★ Trigger Constraint (Extra Credit)"** button, then click **"⚡ Test Atomic Rollback"**, or run `./run_viva_console.sh --q4`.*

> **Spoken**:
> "Now turning to Question 4: **How does our database protect data correctness?**
> 
> **Integrity Constraints**:
> - We enforce **NOT NULL** on critical security fields including `document_number`, `sha256_hash`, `email`, and `entry_hash`.
> - We enforce **UNIQUE constraints** on business keys: `users.email`, `workspaces.code`, `documents.document_number`, and `audit_logs.entry_hash`.
> - We enforce strict **FOREIGN KEY** relationships with explicit cascade definitions.
> - **Database vs Application Division**: The database kernel enforces referential integrity, unique constraints, and nullability. The application layer enforces dynamic Attribute-Based Access Control (ABAC), Bell-LaPadula multi-level security ('No Read Up, No Write Down'), and RSA cryptographic signature verification before staging transactions.
> 
> **Multi-Table Atomic Transactions**:
> When a user uploads a new document or version, it is executed inside a single ACID transaction block:
> 1. Insert into `documents`
> 2. Insert into `document_versions` with SHA-256 calculation
> 3. Compute the cryptographic hash chain link and insert into `audit_logs`
> If any step fails—for example, if disk writes fail or the audit hash collisions occur—the entire transaction is rolled back via `db.rollback()`, ensuring zero orphaned documents exist without an audit trail.
> 
> Let's test this live: I am clicking **'⚡ Test Atomic Rollback'**. As shown in the output, when a fault is injected halfway, `records_persisted` is strictly `False`. Zero records leaked into storage.
> 
> **EXTRA CREDIT DEMONSTRATION**:
> Now I will demonstrate our database kernel rejecting invalid data live on screen!
> I am clicking **'★ Trigger Constraint Rejection'**. 
> As you can see in red on the screen: The SQLite database kernel caught the violation immediately:
> `UNIQUE constraint failed: documents.document_number`.
> The database automatically aborted the insert and rolled back the transaction, preserving data correctness. This demonstrates our database integrity constraints actively defending the vault."

---

### [7:15 – 8:45] QUESTION 5: DATABASE EFFICIENCY, INDEXES & 100X SCALING STRATEGY
**Visual Cue**: *Click **"🔍 EXPLAIN Index Plan"** button in DBMS Studio or run `./run_viva_console.sh --q5` in the terminal.*

> **Spoken**:
> "Finally, Question 5: **How did we make database usage efficient, and what is our 100x scaling strategy?**
> 
> **Indexes Created**:
> We created targeted B-Tree indexes on high-frequency query paths:
> 1. `ix_document_versions_sha256_hash`: Allows $O(\log N)$ logarithmic verification to detect duplicate files or verify tamper seals instantaneously.
> 2. `ix_documents_workspace_id` and `ix_documents_classification`: Accelerates clearance filtering and case dossier pagination.
> 3. `ix_audit_logs_sequence_number` and `ix_audit_logs_entry_hash`: Powers sub-millisecond tamper-evident ledger validation.
> 4. `ix_users_email` and `ix_workspaces_code`: Powers instant authentication and routing.
> 
> **Live EXPLAIN QUERY PLAN Demonstration**:
> On screen, I have executed `EXPLAIN QUERY PLAN` on our indexed query versus an unindexed query:
> - For our indexed lookup on `sha256_hash`, the database optimizer reports: 
>   `SEARCH TABLE document_versions USING INDEX ix_document_versions_sha256_hash`. This executes in $O(\log N)$ time.
> - In contrast, searching an unindexed text field requires `SCAN TABLE documents`, which is an $O(N)$ full table scan.
> 
> **Indexes Considered and Rejected**:
> - We considered indexing `audit_logs.details_json`, but rejected it due to **write amplification**. Audit records are written on every action; rebalancing a B-tree on freeform JSON strings would severely degrade ingestion throughput.
> - We also rejected standalone indexes on low-cardinality boolean flags like `is_deleted` or `is_active`. With only two possible values, B-tree selectivity is negligible, and query optimizers default to table scans anyway.
> 
> **100x Growth Scaling Strategy**:
> If DocuVault's user base grew 100 times, the first components to break would be the monolithic append-only audit table and local disk storage. 
> To handle 100x scale, our architectural remediation is:
> 1. **Range Partitioning**: Partition `audit_logs` by year and month (`PARTITION BY RANGE (timestamp)`), keeping active partitions hot in memory.
> 2. **Read Replicas**: Route write transactions and cryptographic chaining to the primary database, while directing clearance lookups and dossier searches to streaming read replicas.
> 3. **Blob Storage Decoupling**: Decouple raw file bytes from the database host to Cloud Object Storage (S3 / Google Cloud Storage with CMEK), storing only immutable SHA-256 fingerprint pointers in the relational database.
> 4. **In-Memory Caching**: Cache user positions, clearance tiers, and session tokens in Redis with strict invalidation hooks upon position changes."

---

### [8:45 – 9:15] CONCLUSION & SUBMISSION WRAP-UP
**Visual Cue**: *Return to DocuVault main screen showing the pristine audit ledger badge and green status dot.*

> **Spoken**:
> "In conclusion, DocuVault demonstrates that a properly architected Relational Database—with normalized schemas, cascading referential integrity, ACID atomic transactions, targeted B-tree indexing, and controlled denormalization—is the optimal foundation for legal, governmental, and enterprise document security.
> 
> All required queries, schema definitions, transactions, and constraint rejection tests have been demonstrated live from our working application and database console.
> 
> Thank you for your time and evaluation."

---

## 📋 Quick Checklist Before Submitting

- [ ] Video length is under 10 minutes (target 8:00 - 9:00).
- [ ] Screen remained visible with active project UI / terminal throughout the recording.
- [ ] Answered all 5 questions specifically using DocuVault's schema and code.
- [ ] Showed live multi-table JOIN query output.
- [ ] Showed live constraint rejection (Extra Credit!).
- [ ] Upload video to Google Drive or YouTube (unlisted).
- [ ] Submit video link via Google Form: [Form Submission URL](https://docs.google.com/forms/d/e/1FAIpQLSdo3uWnx-u5kdX7iegqCnvTd1TCADkRZMqGKrK6Ld3U4QSATQ/viewform?usp=header).
