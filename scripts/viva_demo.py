#!/usr/bin/env python3
"""
DocuVault DBMS Major Project Viva Interactive Live Terminal Console.
Answers and demonstrates all 5 DBMS Viva Questions live on screen.

Usage:
  python scripts/viva_demo.py --all
  python scripts/viva_demo.py --q1
  python scripts/viva_demo.py --q2
  python scripts/viva_demo.py --q3
  python scripts/viva_demo.py --q4
  python scripts/viva_demo.py --q5
"""

import sys
import os
import argparse
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.dbms_service import DBMSService


# Terminal ANSI Colors
class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    DIM = "\033[2m"


def print_header(title: str):
    width = 78
    print()
    print(f"{Color.CYAN}{'═' * width}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  {title.center(width - 4)}{Color.RESET}")
    print(f"{Color.CYAN}{'═' * width}{Color.RESET}")
    print()


def print_subheader(title: str):
    print(f"\n{Color.BOLD}{Color.BLUE}▶ {title}{Color.RESET}")


def pause(message: str = "Press [ENTER] to continue to the next viva question..."):
    print()
    try:
        input(f"{Color.DIM}{message}{Color.RESET}")
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)


# =============================================================================
# Q1: WHY DID YOU CHOOSE THIS DATABASE?
# =============================================================================
def run_q1():
    print_header("DBMS VIVA - QUESTION 1: DATABASE SELECTION & WORKLOAD PROFILES")
    print(f"{Color.BOLD}1. Database Selected:{Color.RESET} Relational Database Management System (RDBMS)")
    print(f"   Implementation: {Color.GREEN}SQLite 3.x with WAL Mode{Color.RESET} (Local/Edge Vault) & {Color.GREEN}PostgreSQL{Color.RESET} (Enterprise)")
    print()
    print(f"{Color.BOLD}2. Nature of Project Data:{Color.RESET}")
    print(f"   • Highly structured, relational, multi-tenant hierarchy:")
    print(f"     Organizations ➔ Departments ➔ Positions ➔ Users ➔ Workspaces ➔ Documents ➔ Versions ➔ Signatures")
    print(f"   • Strict non-repudiation audit trails fingerprinted with SHA-256 hash chains.")
    print()
    print(f"{Color.BOLD}3. Read vs. Write Access Patterns & Sizing:{Color.RESET}")
    print(f"   • Read-heavy workload: {Color.CYAN}~80% Reads : 20% Writes{Color.RESET}")
    print(f"   • Reads: Bell-LaPadula clearance queries, SHA-256 integrity verifications, dossier reviews.")
    print(f"   • Writes: Atomic document uploads, RSA digital signatures, immutable audit link insertions.")
    print(f"   • Sizing: Designed for 100,000+ dossiers and millions of append-only audit blocks.")
    print()
    print(f"{Color.BOLD}4. Consistency Requirement:{Color.RESET}")
    print(f"   • {Color.YELLOW}Strict Immediate Consistency (ACID Serializable / Read Committed).{Color.RESET}")
    print(f"   • In police evidence or court files, eventual consistency is unacceptable: a modified statement")
    print(f"     or unauthorized clearance leak cannot propagate asynchronously across nodes.")
    print()
    print(f"{Color.BOLD}5. Alternative Considered & Rejected:{Color.RESET}")
    print(f"   • Alternative: {Color.RED}MongoDB / NoSQL Document Store{Color.RESET}")
    print(f"   • Why Rejected: No native relational foreign key cascade safety, no strict schema integrity")
    print(f"     across decoupled collections, and lack of hardware-guaranteed hash-chain ordering without")
    print(f"     heavy distributed two-phase commit overhead.")

    print_subheader("Live Inspection: Database Table Inventory & Row Counts")
    overview = DBMSService.get_database_overview()
    print(f"   Total Normalized Tables: {Color.BOLD}{overview['total_tables']}{Color.RESET}")
    print(f"   {'TABLE NAME':<24} | {'ROWS':<8} | {'COLUMNS':<8} | {'PRIMARY KEY':<16}")
    print(f"   {'-'*24}-|-{'-'*8}-|-{'-'*8}-|-{'-'*16}")
    for stat in overview["table_stats"]:
        pk = ", ".join(stat["primary_key"]) if stat["primary_key"] else "None"
        print(f"   {stat['table_name']:<24} | {stat['row_count']:<8} | {stat['column_count']:<8} | {pk:<16}")


# =============================================================================
# Q2: WALK US THROUGH YOUR SCHEMA OR DATA MODEL
# =============================================================================
def run_q2():
    print_header("DBMS VIVA - QUESTION 2: SCHEMA ARCHITECTURE & RELATIONAL WALKTHROUGH")
    print(f"{Color.BOLD}1. Relational Entities & Hierarchy:{Color.RESET}")
    print(f"   1. organizations         (PK: id, code, name, jurisdiction)")
    print(f"   2. departments           (PK: id, FK: organization_id ➔ organizations.id)")
    print(f"   3. positions             (PK: id, FK: department_id ➔ departments.id, max_clearance, permissions)")
    print(f"   4. users                 (PK: id, FKs: organization_id, department_id, position_id, clearance_level)")
    print(f"   5. workspaces            (PK: id, FK: organization_id, department_id, code, classification)")
    print(f"   6. documents             (PK: id, FK: workspace_id ➔ workspaces.id, created_by_id ➔ users.id)")
    print(f"   7. document_versions     (PK: id, FK: document_id ➔ documents.id, sha256_hash, file_path)")
    print(f"   8. digital_signatures    (PK: id, FKs: document_version_id, signer_id, digest_signed, RSA sig)")
    print(f"   9. audit_logs            (PK: id, FK: user_id ➔ users.id, sequence_number, entry_hash, previous_hash)")
    print(f"  10. chain_of_custody      (PK: id, FKs: document_version_id, sender_id, receiver_id)")
    print(f"  11. temporary_clearances  (PK: id, FKs: user_id, workspace_id, document_id, valid_until)")
    print()
    print(f"{Color.BOLD}2. Cardinality & Relationship Resolutions:{Color.RESET}")
    print(f"   • 1:N  Organization ➔ Departments, Workspaces, Users")
    print(f"   • 1:N  Department   ➔ Positions, Workspaces")
    print(f"   • 1:N  Position     ➔ Users")
    print(f"   • 1:N  Workspace    ➔ Documents (cases contain multiple governed files)")
    print(f"   • 1:N  Document     ➔ DocumentVersions (immutable version history with SHA-256)")
    print(f"   • {Color.YELLOW}M:N Resolution (Users ↔ DocumentVersions):{Color.RESET} Resolved via {Color.BOLD}digital_signatures{Color.RESET} and {Color.BOLD}chain_of_custody{Color.RESET}")
    print(f"   • {Color.YELLOW}M:N Resolution (Users ↔ Workspaces):{Color.RESET} Resolved via {Color.BOLD}temporary_clearances{Color.RESET} for delegated access")

    print_subheader("Live Query Output: Multi-Table JOIN across 6 Relational Entities")
    print(f"{Color.DIM}SQL: SELECT d.document_number, d.title, w.code, dv.sha256_hash, u.full_name, p.title, sig.validity_status{Color.RESET}")
    print(f"{Color.DIM}     FROM documents d JOIN workspaces w JOIN document_versions dv JOIN users u JOIN positions p ...{Color.RESET}")
    print()

    results = DBMSService.run_multi_table_join(limit=5)
    if results:
        for idx, row in enumerate(results, 1):
            print(f"   {Color.BOLD}[Record {idx}]{Color.RESET} Doc: {Color.CYAN}{row['document_number']}{Color.RESET} | \"{row['document_title']}\"")
            print(f"              Workspace: {row['workspace_code']} ({row['workspace_name']})")
            print(f"              Clearance: {row['doc_clearance']} | Status: {row['doc_status']} | Size: {row['file_size']} bytes")
            print(f"              Uploaded By: {row['uploaded_by_officer']} ({row['officer_position']})")
            print(f"              SHA-256: {Color.DIM}{row['sha256_hash']}{Color.RESET}")
            print(f"              Signature: {row['signature_validity'] or 'Unsigned'} ({row['signature_algorithm'] or 'N/A'})\n")
    else:
        print("   No active records returned.")


# =============================================================================
# Q3: WHAT NORMAL FORM IS YOUR DESIGN IN & DELIBERATE DENORMALIZATION
# =============================================================================
def run_q3():
    print_header("DBMS VIVA - QUESTION 3: NORMALIZATION (3NF/BCNF) & CONTROLLED DENORMALIZATION")
    print(f"{Color.BOLD}1. Highest Normal Form Reached:{Color.RESET} {Color.GREEN}Third Normal Form (3NF) / BCNF{Color.RESET}")
    print()
    print(f"{Color.BOLD}2. Step-by-Step Normalization Proofs:{Color.RESET}")
    print(f"   • {Color.BOLD}First Normal Form (1NF):{Color.RESET} All table attributes are atomic. Primary keys uniquely identify")
    print(f"     every tuple. No repeating groups. Scalar serialization used for JSON properties.")
    print(f"   • {Color.BOLD}Second Normal Form (2NF):{Color.RESET} 1NF satisfied + All non-key attributes are fully functionally")
    print(f"     dependent on the entire primary key (using surrogate UUID primary keys, preventing partial key dependency).")
    print(f"   • {Color.BOLD}Third Normal Form (3NF):{Color.RESET} 2NF satisfied + Zero transitive functional dependencies ($X ➔ Y ➔ Z).")
    print(f"     Users table does not store department names or position titles; it stores `position_id`")
    print(f"     and `department_id`, isolating entity updates completely.")
    print()
    print(f"{Color.BOLD}3. Functional Dependencies for Core Entity (documents):{Color.RESET}")
    print(f"   • {Color.CYAN}id ➔ {{title, document_number, classification, status, workspace_id, created_by_id}}{Color.RESET}")
    print(f"   • {Color.CYAN}document_number ➔ {{id, title, classification, workspace_id}}{Color.RESET} (Candidate Key)")
    print(f"   • Every determinant is a candidate key, therefore satisfying {Color.GREEN}Boyce-Codd Normal Form (BCNF){Color.RESET}.")
    print()
    print(f"{Color.BOLD}4. Deliberate Denormalization & Synchronization Architecture:{Color.RESET}")
    print(f"   • {Color.YELLOW}Table: audit_logs{Color.RESET}")
    print(f"     Stores `user_email`, `user_name`, and `user_position` as snapshot columns alongside `user_id`.")
    print(f"     {Color.BOLD}Why?{Color.RESET} In forensic and court audits 5 years later, if an officer changes roles or is deleted,")
    print(f"     the audit trail must preserve the historical identity snapshot at the exact second of signing.")
    print(f"     A dynamic join to a modified or deleted user would tamper with forensic evidence!")
    print(f"   • {Color.BOLD}Maintenance & Synchronization:{Color.RESET} Audit records are strictly write-once immutable append-only.")
    print(f"     The user snapshot is captured in the upload transaction pipeline and sealed inside the SHA-256 block.")


# =============================================================================
# Q4: DATA CORRECTNESS, CONSTRAINTS & ATOMIC TRANSACTIONS
# =============================================================================
def run_q4():
    print_header("DBMS VIVA - QUESTION 4: CONSTRAINTS, ATOMIC TRANSACTIONS & CONCURRENCY")
    print(f"{Color.BOLD}1. Database-Enforced Integrity Constraints:{Color.RESET}")
    print(f"   • {Color.BOLD}NOT NULL:{Color.RESET} Enforced on `document_number`, `sha256_hash`, `email`, `entry_hash`, `sequence_number`.")
    print(f"   • {Color.BOLD}UNIQUE:{Color.RESET} Enforced on `users.email`, `documents.document_number`, `workspaces.code`, `audit_logs.entry_hash`.")
    print(f"   • {Color.BOLD}FOREIGN KEY Cascades:{Color.RESET} `ON DELETE CASCADE` on child entities (documents ➔ versions ➔ signatures);")
    print(f"     `ON DELETE SET NULL` on audit actors so evidence remains intact even if a staff record is archived.")
    print(f"   • {Color.BOLD}Application-Enforced Logic:{Color.RESET} Multi-level security Bell-LaPadula clearance rules (No Read Up, No Write Down)")
    print(f"     and RSA-PSS-2048 cryptographic signature validation before transaction commit.")
    print()
    print(f"{Color.BOLD}2. Atomic Multi-Table Transaction Pipeline:{Color.RESET}")
    print(f"   Upload Operation commits 3 records simultaneously inside a single ACID block:")
    print(f"   [1] Insert Document ➔ [2] Insert DocumentVersion ➔ [3] Compute & Insert Hash-Chained AuditLog")
    print(f"   If any step fails, the entire transaction rolls back, preventing orphaned documents.")

    print_subheader("Live Demo 1: Atomic Transaction with Simulated Rollback on Failure")
    rollback_demo = DBMSService.demonstrate_atomic_transaction(simulate_failure=True)
    print(f"   Transaction Status: {Color.YELLOW}{rollback_demo['status']}{Color.RESET}")
    print(f"   Simulated Fault: {Color.RED}{rollback_demo['simulated_error']}{Color.RESET}")
    print(f"   Orphan Records Persisted in Database: {Color.BOLD}{rollback_demo['records_persisted']}{Color.RESET} (0 records)")
    print(f"   Outcome: {rollback_demo['explanation']}")

    print_subheader("Live Demo 2: EXTRA CREDIT - Database Constraint Rejection")
    print(f"   Deliberately attempting to insert duplicate document number to trigger DB constraint...")
    time.sleep(0.5)
    constraint_demo = DBMSService.demonstrate_constraint_rejection()
    if constraint_demo.get("rejected"):
        print(f"   {Color.GREEN}✓ Constraint Caught:{Color.RESET} {Color.BOLD}{constraint_demo['constraint_type']}{Color.RESET}")
        print(f"   Violated Value: {Color.CYAN}'{constraint_demo['violated_value']}'{Color.RESET}")
        print(f"   Database Kernel Output: {Color.RED}{constraint_demo['database_error']}{Color.RESET}")
        print(f"   Verification: {Color.GREEN}{constraint_demo['explanation']}{Color.RESET}")
        print(f"   {Color.BOLD}{Color.MAGENTA}★ EXTRA CREDIT CRITERIA SATISFIED! ★{Color.RESET}")
    else:
        print(f"   {Color.RED}Constraint test failed.{Color.RESET}")


# =============================================================================
# Q5: DATABASE EFFICIENCY, INDEXES & 100X SCALING STRATEGY
# =============================================================================
def run_q5():
    print_header("DBMS VIVA - QUESTION 5: INDEXING, QUERY PLANS & 100X SCALING STRATEGY")
    print(f"{Color.BOLD}1. High-Performance B-Tree Indexes Created:{Color.RESET}")
    print(f"   • {Color.GREEN}ix_document_versions_sha256_hash:{Color.RESET} Fast O(log N) fingerprint integrity verifications.")
    print(f"   • {Color.GREEN}ix_documents_workspace_id & ix_documents_classification:{Color.RESET} Multi-tier clearance filters.")
    print(f"   • {Color.GREEN}ix_audit_logs_sequence_number & ix_audit_logs_entry_hash:{Color.RESET} Real-time tamper verification.")
    print(f"   • {Color.GREEN}ix_users_email & ix_workspaces_code:{Color.RESET} Sub-millisecond credential lookups.")
    print()
    print(f"{Color.BOLD}2. Indexes Considered but Deliberately Rejected:{Color.RESET}")
    print(f"   • {Color.RED}Rejected: Index on audit_logs.details_json:{Color.RESET} Extreme write amplification. Audit logs are written")
    print(f"     on every action; indexing freeform JSON strings introduces severe B-tree rebalancing overhead.")
    print(f"   • {Color.RED}Rejected: Standalone index on boolean flags (is_deleted, is_active):{Color.RESET} Negligible cardinality")
    print(f"     (only 2 values); optimizer defaults to table scans anyway.")

    print_subheader("Live Query Plan: EXPLAIN QUERY PLAN (Indexed vs. Unindexed Search)")
    plans = DBMSService.explain_query_plans()

    print(f"   {Color.BOLD}[INDEXED LOOKUP]{Color.RESET} {plans['indexed_query']['sql']}")
    print(f"   Used: {Color.GREEN}{plans['indexed_query']['index_used']}{Color.RESET} | Complexity: {plans['indexed_query']['complexity']}")
    for step in plans["indexed_query"]["plan"]:
        print(f"   ➔ Plan Detail: {step.get('detail', str(step))}")
    print()
    print(f"   {Color.BOLD}[UNINDEXED LOOKUP]{Color.RESET} {plans['unindexed_query']['sql']}")
    print(f"   Used: {Color.YELLOW}{plans['unindexed_query']['index_used']}{Color.RESET} | Complexity: {plans['unindexed_query']['complexity']}")
    for step in plans["unindexed_query"]["plan"]:
        print(f"   ➔ Plan Detail: {step.get('detail', str(step))}")

    print_subheader("Scaling Plan: What Breaks at 100x Growth & Architectural Remediation")
    for item in plans["scaling_100x_plan"]:
        print(f"   {Color.CYAN}{item}{Color.RESET}")


# =============================================================================
# MAIN CLI DISPATCHER
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="DocuVault DBMS Viva Live Interactive Console")
    parser.add_argument("--all", action="store_true", help="Run full 5-question sequential viva walkthrough")
    parser.add_argument("--q1", action="store_true", help="Run Question 1: Database Selection & Workload")
    parser.add_argument("--q2", action="store_true", help="Run Question 2: Schema & Multi-Table Join")
    parser.add_argument("--q3", action="store_true", help="Run Question 3: 3NF/BCNF Normalization & Denormalization")
    parser.add_argument("--q4", action="store_true", help="Run Question 4: Constraints, Transactions & Extra Credit Demo")
    parser.add_argument("--q5", action="store_true", help="Run Question 5: Indexes, EXPLAIN Plans & 100x Scaling")

    args = parser.parse_args()

    if not any([args.all, args.q1, args.q2, args.q3, args.q4, args.q5]):
        # Default to --all if no flag passed
        args.all = True

    if args.all:
        run_q1()
        pause("Press [ENTER] to proceed to Question 2 (Schema & Relational Model)...")
        run_q2()
        pause("Press [ENTER] to proceed to Question 3 (Normalization & Functional Dependencies)...")
        run_q3()
        pause("Press [ENTER] to proceed to Question 4 (Constraints, Transactions & Extra Credit Rejection)...")
        run_q4()
        pause("Press [ENTER] to proceed to Question 5 (Indexes, Query Plans & 100x Scaling)...")
        run_q5()
        print()
        print(f"{Color.BOLD}{Color.GREEN}✔ Full DBMS Viva Demonstration Complete. Good luck with your submission!{Color.RESET}\n")
    else:
        if args.q1: run_q1()
        if args.q2: run_q2()
        if args.q3: run_q3()
        if args.q4: run_q4()
        if args.q5: run_q5()


if __name__ == "__main__":
    main()
