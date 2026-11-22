# DocuVault DBMS Major Project Viva — Concise Voiceover Script

This script is streamlined, direct, and easy to speak naturally. It answers all five questions thoroughly while cutting unnecessary filler, allowing you to comfortably deliver your presentation.

---

### Introduction
Hello professors. My name is Sahil Shingate, and this is my individual video submission for the Data Engineering Major Project DBMS Viva. 

My project is DocuVault, a secure, DigiLocker-grade document management and cryptographic provenance system. In organizations like police stations, courts, and corporate enterprises, sensitive documents are often scattered across unencrypted network drives. If a court statement is altered, it can overturn a trial; if an enterprise contract leaks, it causes severe financial damage. 

DocuVault solves this through strict multi-level clearance access control, SHA-256 fingerprinting, RSA digital signatures, and an immutable, hash-chained audit ledger. My screen will remain visible throughout this video as I demonstrate our real database schema, code, live queries, and constraint validations.

---

### Question 1: Why Did You Choose This Database?
We chose a Relational Database Management System (RDBMS), implemented using SQLite 3 with Write-Ahead Logging for edge deployments and PostgreSQL for enterprise configurations, managed via SQLAlchemy ORM.

Our data is highly structured, strongly typed, and hierarchical, flowing from Organizations to Departments, Positions, Users, Workspaces, Documents, Document Versions, Signatures, and Audit Logs. 

Our access pattern is read-heavy, roughly 80% reads and 20% writes. Reads handle security clearance lookups, SHA-256 file integrity checks, and case dossier queries. Writes occur during critical atomic operations: uploading new document versions, recording cryptographic signatures, and appending immutable audit blocks.

We require strict Immediate Consistency with full ACID guarantees. In court evidence, eventual consistency is unacceptable: if an officer's clearance is revoked or a file is placed under judicial seal, that restriction must take effect immediately across all transactions.

We evaluated MongoDB and document stores, but rejected them because they lack native cascading foreign keys, cannot guarantee referential integrity across separate collections, and cannot reliably enforce ordered hash-chain serialization during network partitions without heavy two-phase commit overhead.

---

### Question 2: Schema Architecture & Relational Model Walkthrough
Our schema consists of 11 normalized tables:
- Organizations, Departments, and Positions establish institutional boundaries, ranks like Superintendent of Police or District Judge, and clearance limits.
- Users stores officer identities, credentials, public cryptographic keys, and clearance levels.
- Workspaces represents case files and investigation folders with mandatory security classifications.
- Documents and Document Versions represent governed files, tracking file sizes, MIME types, and SHA-256 content hashes.
- Digital Signatures stores RSA-PSS-2048 cryptographic signatures linked directly to a document version's digest.
- Audit Logs maintains our tamper-evident hash chain.
- Chain of Custody and Temporary Clearances manage physical evidence handoffs and time-bound delegated access.

Our relationships include standard 1-to-Many connections between Organizations and Departments, Workspaces and Documents, and Documents and Versions. 

Many-to-Many relationships are cleanly resolved: Users and Document Versions are linked through the Digital Signatures associative table for non-repudiation and Chain of Custody for transfers. Delegated access between Users and Workspaces is resolved through Temporary Clearances.

Referential integrity is strictly enforced: we use ON DELETE CASCADE for parent-child dependencies so versions and signatures are cleaned up if a case is expunged, and ON DELETE SET NULL on user references so historical audit evidence remains intact if an employee leaves.

As you can see in the live 6-table JOIN query output on screen, a single SQL query connects documents, workspaces, versions, uploaded officers, positions, and digital signatures in one unified view.

---

### Question 3: Normal Form Design & Deliberate Denormalization
Our relational design reaches Third Normal Form (3NF) and Boyce-Codd Normal Form (BCNF) across all primary entities:
- First Normal Form is satisfied because all attributes are atomic scalar values and every table has a unique surrogate UUID primary key.
- Second Normal Form is satisfied because single-column surrogate keys eliminate all partial key dependencies.
- Third Normal Form is satisfied because we removed all transitive dependencies. For example, the Users table stores position_id and department_id rather than department names, isolating schema changes completely.
- In Documents, the determinant document_number is a candidate key, satisfying BCNF.

We deliberately broke 3NF in our Audit Logs table: alongside user_id, we store redundant snapshot columns: user_email, user_name, and user_position. 

We did this for legal court admissibility. If an officer changes ranks, resigns, or is deleted five years later, a dynamic relational join to user_id would either return NULL or show their new position, thereby altering historical facts! By taking a permanent identity snapshot at the second of signing, our audit trail preserves historical truth. Correctness is maintained because audit logs are strictly append-only and sealed inside the SHA-256 hash chain upon insertion.

---

### Question 4: Data Correctness, Constraints & Atomic Transactions
Our database actively enforces NOT NULL on critical security fields, UNIQUE constraints on business keys like email, workspace code, and document number, and foreign key cascades. The database kernel enforces referential integrity and uniqueness, while our application code enforces Bell-LaPadula multi-level security clearance and RSA cryptographic signature verification before staging transactions.

Our document upload operation executes as an atomic multi-table transaction committing the Document, Document Version, and hash-chained Audit Log together. If any step fails halfway—such as a disk error or hash collision—everything is rolled back via db.rollback(), leaving zero orphaned records.

As demonstrated on screen in our atomic rollback test, when a simulated fault is injected, zero records are persisted.

For our extra credit demonstration: as seen on screen, when we attempt to insert a duplicate document number, the SQLite kernel immediately rejects the write with: UNIQUE constraint failed: documents.document_number, and rolls back the transaction, actively defending vault integrity.

---

### Question 5: Database Efficiency, Indexes & 100x Scaling Strategy
To maximize performance, we created targeted B-tree indexes:
- ix_document_versions_sha256_hash enables O(log N) logarithmic file verification to detect duplicate files or verify tamper seals instantaneously.
- Covering indexes on workspace_id and classification accelerate clearance filtering.
- Indexes on audit sequence numbers and entry hashes power sub-millisecond tamper checks.

As shown in our live EXPLAIN QUERY PLAN demonstration, searching a document by its SHA-256 hash uses our B-tree index in O(log N) time, while unindexed text fields require an O(N) full table scan.

We deliberately rejected indexing unstructured details_json to prevent heavy write amplification on our high-frequency audit stream, and rejected indexing low-cardinality boolean flags like is_deleted because query optimizers default to table scans anyway.

If DocuVault's workload grew 100 times, our architectural scaling plan is:
1. Range Partitioning: Partition the append-only audit_logs table by year and month.
2. Read Replicas: Direct writes and cryptographic chaining to the primary database, while routing search queries and clearance checks to streaming read replicas.
3. Blob Storage Decoupling: Offload binary file bytes to Cloud Object Storage like S3 or Google Cloud Storage, retaining only immutable SHA-256 fingerprint pointers in the relational database.
4. In-Memory Caching: Cache user clearance tiers and permissions in Redis with event-driven invalidation.

---

### Conclusion
In conclusion, DocuVault demonstrates that a normalized Relational Database—with cascading foreign keys, ACID atomic transactions, targeted B-tree indexes, and controlled denormalization—is the optimal foundation for legal, governmental, and enterprise document security.

All five viva questions, live query outputs, and constraint rejection tests have been demonstrated directly from our working application. Thank you for your time and evaluation.
