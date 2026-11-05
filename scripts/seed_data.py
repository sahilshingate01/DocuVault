"""Seed Data Generator for DocuVault: Police, Judiciary, and Enterprise Scenarios."""
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.core.constants import ClassificationLevel, DocumentStatus, ActionType, ResourceType
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.department import Department
from app.models.position import Position
from app.models.user import User
from app.models.workspace import Workspace
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.signature import DigitalSignature
from app.services.crypto_service import CryptoService
from app.services.storage_service import StorageService
from app.services.audit_service import AuditService


def seed_database():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Check if already seeded
        if db.query(Organization).first():
            print("Database already contains data. Skipping re-seed.")
            return

        print("Seeding Organizations, Departments, and Roles...")

        # -------------------------------------------------------------
        # 1. State Police Department
        # -------------------------------------------------------------
        org_police = Organization(
            name="State Police Department",
            slug="state-police",
            description="State Law Enforcement and Criminal Investigation Agency",
            jurisdiction="State Law Enforcement"
        )
        db.add(org_police)
        db.flush()

        dept_cid = Department(
            name="Criminal Investigation Division (CID)",
            code="CID",
            description="Specialized Major Crimes and Forensic Inquiries",
            organization_id=org_police.id
        )
        db.add(dept_cid)
        db.flush()

        pos_sp = Position(
            title="Superintendent of Police",
            code="SP",
            description="Executive Police Commander with highest security clearance and signing authority",
            max_clearance=ClassificationLevel.TOP_SECRET.value,
            can_sign=True,
            can_approve=True,
            can_export=True,
            can_manage_users=True,
            allowed_actions=["READ", "WRITE", "UPDATE", "APPROVE", "SIGN", "DELETE", "EXPORT"],
            department_id=dept_cid.id
        )
        pos_si = Position(
            title="Investigating Officer",
            code="IO",
            description="Field investigator authorized to write reports and upload evidence",
            max_clearance=ClassificationLevel.CONFIDENTIAL.value,
            can_sign=False,
            can_approve=False,
            can_export=False,
            can_manage_users=False,
            allowed_actions=["READ", "WRITE", "UPDATE"],
            department_id=dept_cid.id
        )
        db.add_all([pos_sp, pos_si])
        db.flush()

        # Keypair for SP
        sp_priv, sp_pub = CryptoService.generate_keypair()
        user_sp = User(
            email="sp.vikram@police.gov.in",
            full_name="SP Vikram Sharma",
            hashed_password=get_password_hash("Password123!"),
            badge_number="IPS-2014-0402",
            clearance_level=ClassificationLevel.TOP_SECRET.value,
            public_key_pem=sp_pub,
            organization_id=org_police.id,
            department_id=dept_cid.id,
            position_id=pos_sp.id
        )
        user_si = User(
            email="arjun.das@police.gov.in",
            full_name="Sub-Inspector Arjun Das",
            hashed_password=get_password_hash("Password123!"),
            badge_number="POL-2020-0891",
            clearance_level=ClassificationLevel.CONFIDENTIAL.value,
            organization_id=org_police.id,
            department_id=dept_cid.id,
            position_id=pos_si.id
        )
        db.add_all([user_sp, user_si])
        db.flush()

        # Police Workspace (Case File)
        ws_police_case = Workspace(
            name="State vs. Vikram Malgudi Homicide Inquiry",
            code="CASE-2026-CR-0402",
            description="Primary homicide investigation and ballistic chain-of-custody dossier",
            workspace_type="CASE",
            classification=ClassificationLevel.CONFIDENTIAL.value,
            organization_id=org_police.id,
            department_id=dept_cid.id
        )
        db.add(ws_police_case)
        db.flush()

        # Document 1: FIR
        fir_content = b"""STATE POLICE DEPARTMENT - CRIMINAL INVESTIGATION DIVISION
FIRST INFORMATION REPORT (Under Section 154 Cr.P.C)
-----------------------------------------------------------
FIR Number: FIR/2026/0402
Date & Time of Occurrence: 2026-10-18 22:45 IST
Complainant: Dr. Arvind Swaminathan
Accused: Vikram Malgudi (Age: 38)
Incident Overview: Armed intrusion and assault with firearm recovered at scene.
Seized Evidence: 9mm semi-automatic pistol, 3 spent casings, digital CCTV hard disk.
Investigating Officer: Sub-Inspector Arjun Das (Badge #0891)
Status: Active Investigation
"""
        fir_path, fir_hash, fir_size = StorageService.save_bytes(fir_content, "FIR_2026_0402.txt")
        doc_fir = Document(
            title="First Information Report (FIR) - Case #0402",
            document_number="DOC-FIR-2026-0402",
            description="Certified police first information report regarding armed intrusion",
            classification=ClassificationLevel.CONFIDENTIAL.value,
            status=DocumentStatus.APPROVED.value,
            tags=["fir", "homicide", "police", "crime"],
            workspace_id=ws_police_case.id,
            created_by_id=user_si.id
        )
        db.add(doc_fir)
        db.flush()

        ver_fir = DocumentVersion(
            version_number=1,
            file_path=fir_path,
            original_filename="FIR_2026_0402.txt",
            file_size=fir_size,
            mime_type="text/plain",
            sha256_hash=fir_hash,
            change_summary="Initial verified FIR registration",
            is_approved=True,
            approved_by_id=user_sp.id,
            document_id=doc_fir.id,
            uploaded_by_id=user_si.id
        )
        db.add(ver_fir)
        db.flush()

        # Document 2: Ballistics Report (Top Secret, Signed by SP)
        bal_content = b"""FORENSIC SCIENCE LABORATORY - BALLISTICS DIVISION
CRIMINAL FORENSICS REPORT - TOP SECRET SENSITIVE
--------------------------------------------------------------
Evidence Reference: FSL-BAL-2026-9912
Target Case: State vs. Vikram Malgudi (CASE-2026-CR-0402)

MICROSCOPIC STRIATION COMPARISON:
Striations on bullet casing recovered from victim vehicle exhibit 100% concordance
with test firings from seized 9mm Glock (Serial #GL-99214).
Primer residue testing confirms firing within 2 hours of apprehension.

CERTIFICATION:
I hereby certify under official seal that this ballistic forensic record is authentic,
tamper-free, and legally admissible in the High Court of Justice.
Signed: Superintendent of Police Vikram Sharma
"""
        bal_path, bal_hash, bal_size = StorageService.save_bytes(bal_content, "Ballistics_Forensics_9912.txt")
        doc_bal = Document(
            title="Ballistics & Striation Forensic Report #9912",
            document_number="DOC-BAL-2026-9912",
            description="Forensic ballistics test matching murder weapon with bullet striations",
            classification=ClassificationLevel.TOP_SECRET.value,
            status=DocumentStatus.SIGNED.value,
            tags=["ballistics", "forensics", "classified", "glock"],
            workspace_id=ws_police_case.id,
            created_by_id=user_sp.id
        )
        db.add(doc_bal)
        db.flush()

        ver_bal = DocumentVersion(
            version_number=1,
            file_path=bal_path,
            original_filename="Ballistics_Forensics_9912.txt",
            file_size=bal_size,
            mime_type="text/plain",
            sha256_hash=bal_hash,
            change_summary="Certified ballistic striation analysis",
            is_approved=True,
            approved_by_id=user_sp.id,
            document_id=doc_bal.id,
            uploaded_by_id=user_sp.id
        )
        db.add(ver_bal)
        db.flush()

        # Sign ballistics report with SP's key
        sig_bal_hex = CryptoService.sign_digest(sp_priv, bal_hash)
        sig_bal = DigitalSignature(
            signature_hex=sig_bal_hex,
            public_key_pem=sp_pub,
            algorithm="RSA-PSS-SHA256",
            digest_signed=bal_hash,
            signer_title="Superintendent of Police",
            validity_status="VALID",
            document_version_id=ver_bal.id,
            signer_id=user_sp.id
        )
        db.add(sig_bal)
        db.flush()

        # -------------------------------------------------------------
        # 2. District Court of Justice
        # -------------------------------------------------------------
        org_court = Organization(
            name="District Court of Justice",
            slug="district-court",
            description="Judicial Court of District Administration",
            jurisdiction="Judiciary"
        )
        db.add(org_court)
        db.flush()

        dept_registry = Department(
            name="Judicial Registry & Chambers",
            code="JUD-REG",
            description="Presiding judges, court registries, and judicial depositions",
            organization_id=org_court.id
        )
        db.add(dept_registry)
        db.flush()

        pos_judge = Position(
            title="Principal District Judge",
            code="PDJ",
            description="Presiding judicial officer with supreme judicial signing and decree powers",
            max_clearance=ClassificationLevel.TOP_SECRET.value,
            can_sign=True,
            can_approve=True,
            can_export=True,
            can_manage_users=True,
            allowed_actions=["READ", "WRITE", "UPDATE", "APPROVE", "SIGN", "EXPORT"],
            department_id=dept_registry.id
        )
        pos_clerk = Position(
            title="Court Record Clerk",
            code="CRC",
            description="Record keeper authorized to catalogue filings with restricted clearance",
            max_clearance=ClassificationLevel.RESTRICTED.value,
            can_sign=False,
            can_approve=False,
            can_export=False,
            can_manage_users=False,
            allowed_actions=["READ", "WRITE"],
            department_id=dept_registry.id
        )
        db.add_all([pos_judge, pos_clerk])
        db.flush()

        judge_priv, judge_pub = CryptoService.generate_keypair()
        user_judge = User(
            email="sneha.kulkarni@judiciary.gov.in",
            full_name="Hon. Judge Sneha Kulkarni",
            hashed_password=get_password_hash("Password123!"),
            badge_number="JUD-GJ-0012",
            clearance_level=ClassificationLevel.TOP_SECRET.value,
            public_key_pem=judge_pub,
            organization_id=org_court.id,
            department_id=dept_registry.id,
            position_id=pos_judge.id
        )
        user_clerk = User(
            email="manoj.verma@judiciary.gov.in",
            full_name="Manoj Verma",
            hashed_password=get_password_hash("Password123!"),
            badge_number="CLK-2018-034",
            clearance_level=ClassificationLevel.RESTRICTED.value,
            organization_id=org_court.id,
            department_id=dept_registry.id,
            position_id=pos_clerk.id
        )
        db.add_all([user_judge, user_clerk])
        db.flush()

        # Court Workspace
        ws_court = Workspace(
            name="Commercial Anti-Corruption Proceedings",
            code="CASE-2026-JUD-0918",
            description="Judicial proceedings regarding anti-corruption and asset seizures",
            workspace_type="CASE",
            classification=ClassificationLevel.SECRET.value,
            organization_id=org_court.id,
            department_id=dept_registry.id
        )
        db.add(ws_court)
        db.flush()

        # Judicial Order (Signed by Judge)
        order_content = b"""IN THE COURT OF THE PRINCIPAL DISTRICT & SESSIONS JUDGE
ORDER ON INTERIM INJUNCTION & ASSET FREEZE (CASE #0918)
-------------------------------------------------------
Coram: Hon'ble Justice Sneha Kulkarni
Petitioner: Special Enforcement Directorate
Respondent: Horizon Infrastructure Private Limited

Upon perusal of forensic audit logs and witness testimonies filed under sealed cover:
1. The Court hereby orders an immediate freeze on all offshore banking assets of the Respondent.
2. Directs the registry to seal all relevant project contracts under 'TOP SECRET' classification.
3. Violation of this decree will attract immediate contempt proceedings.

Given under my hand and official seal of the Court.
"""
        order_path, order_hash, order_size = StorageService.save_bytes(order_content, "Judicial_Order_0918.txt")
        doc_order = Document(
            title="Judicial Asset Freeze Decree & Injunction Order",
            document_number="DOC-JUD-ORDER-0918",
            description="Binding court decree on asset seizure and corporate restraint",
            classification=ClassificationLevel.TOP_SECRET.value,
            status=DocumentStatus.SIGNED.value,
            tags=["court", "order", "injunction", "decree", "judge"],
            workspace_id=ws_court.id,
            created_by_id=user_judge.id
        )
        db.add(doc_order)
        db.flush()

        ver_order = DocumentVersion(
            version_number=1,
            file_path=order_path,
            original_filename="Judicial_Order_0918.txt",
            file_size=order_size,
            mime_type="text/plain",
            sha256_hash=order_hash,
            change_summary="Judicial decree issued and digitally sealed",
            is_approved=True,
            approved_by_id=user_judge.id,
            document_id=doc_order.id,
            uploaded_by_id=user_judge.id
        )
        db.add(ver_order)
        db.flush()

        sig_order_hex = CryptoService.sign_digest(judge_priv, order_hash)
        sig_order = DigitalSignature(
            signature_hex=sig_order_hex,
            public_key_pem=judge_pub,
            algorithm="RSA-PSS-SHA256",
            digest_signed=order_hash,
            signer_title="Principal District Judge",
            validity_status="VALID",
            document_version_id=ver_order.id,
            signer_id=user_judge.id
        )
        db.add(sig_order)
        db.flush()

        # -------------------------------------------------------------
        # 3. Enterprise: Apex Cybernetics Corp
        # -------------------------------------------------------------
        org_corp = Organization(
            name="Apex Cybernetics Corporation",
            slug="apex-corp",
            description="Global Enterprise and Advanced Software Systems",
            jurisdiction="Corporate Enterprise"
        )
        db.add(org_corp)
        db.flush()

        dept_exec = Department(
            name="Executive Leadership & M&A",
            code="CORP-EXEC",
            description="Mergers, corporate finance, and executive board governance",
            organization_id=org_corp.id
        )
        db.add(dept_exec)
        db.flush()

        pos_ceo = Position(
            title="Chief Executive Officer",
            code="CEO",
            description="Corporate executive with full contract signing authority",
            max_clearance=ClassificationLevel.TOP_SECRET.value,
            can_sign=True,
            can_approve=True,
            can_export=True,
            can_manage_users=True,
            allowed_actions=["READ", "WRITE", "UPDATE", "APPROVE", "SIGN", "DELETE", "EXPORT"],
            department_id=dept_exec.id
        )
        pos_analyst = Position(
            title="Junior Analyst",
            code="ANA",
            description="Junior associate with general unclassified access",
            max_clearance=ClassificationLevel.UNCLASSIFIED.value,
            can_sign=False,
            can_approve=False,
            can_export=False,
            can_manage_users=False,
            allowed_actions=["READ"],
            department_id=dept_exec.id
        )
        db.add_all([pos_ceo, pos_analyst])
        db.flush()

        ceo_priv, ceo_pub = CryptoService.generate_keypair()
        user_ceo = User(
            email="siddharth@apexcorp.com",
            full_name="Siddharth Singhania",
            hashed_password=get_password_hash("Password123!"),
            badge_number="EMP-0001",
            clearance_level=ClassificationLevel.TOP_SECRET.value,
            public_key_pem=ceo_pub,
            organization_id=org_corp.id,
            department_id=dept_exec.id,
            position_id=pos_ceo.id
        )
        user_analyst = User(
            email="riya.sen@apexcorp.com",
            full_name="Riya Sen",
            hashed_password=get_password_hash("Password123!"),
            badge_number="EMP-4109",
            clearance_level=ClassificationLevel.UNCLASSIFIED.value,
            organization_id=org_corp.id,
            department_id=dept_exec.id,
            position_id=pos_analyst.id
        )
        db.add_all([user_ceo, user_analyst])
        db.flush()

        ws_corp = Workspace(
            name="Project Titan Acquisition Dossier",
            code="CORP-MA-2026",
            description="Strictly confidential merger & acquisition due-diligence archive",
            workspace_type="PROJECT",
            classification=ClassificationLevel.CONFIDENTIAL.value,
            organization_id=org_corp.id,
            department_id=dept_exec.id
        )
        db.add(ws_corp)
        db.flush()

        contract_content = b"""APEX CYBERNETICS CORP - CONFIDENTIAL MERGER TERM SHEET
PROJECT TITAN: BINDING ACQUISITION AGREEMENT
------------------------------------------------------
Valuation: $450,000,000 USD
Parties: Apex Cybernetics Corp & Solaria Technologies LLC
Governing Terms: All intellectual property, neural patents, and customer pipelines
transfer upon formal digital execution.

Authorized Signatory: Siddharth Singhania, CEO
"""
        corp_path, corp_hash, corp_size = StorageService.save_bytes(contract_content, "Titan_Merger_Agreement.txt")
        doc_contract = Document(
            title="Binding M&A Term Sheet - Project Titan",
            document_number="DOC-CORP-AGR-001",
            description="Executed corporate acquisition agreement with Solaria Tech",
            classification=ClassificationLevel.CONFIDENTIAL.value,
            status=DocumentStatus.SIGNED.value,
            tags=["merger", "contract", "acquisition", "corporate"],
            workspace_id=ws_corp.id,
            created_by_id=user_ceo.id
        )
        db.add(doc_contract)
        db.flush()

        ver_contract = DocumentVersion(
            version_number=1,
            file_path=corp_path,
            original_filename="Titan_Merger_Agreement.txt",
            file_size=corp_size,
            mime_type="text/plain",
            sha256_hash=corp_hash,
            change_summary="Final board ratified acquisition agreement",
            is_approved=True,
            approved_by_id=user_ceo.id,
            document_id=doc_contract.id,
            uploaded_by_id=user_ceo.id
        )
        db.add(ver_contract)
        db.flush()

        sig_corp_hex = CryptoService.sign_digest(ceo_priv, corp_hash)
        sig_corp = DigitalSignature(
            signature_hex=sig_corp_hex,
            public_key_pem=ceo_pub,
            algorithm="RSA-PSS-SHA256",
            digest_signed=corp_hash,
            signer_title="Chief Executive Officer",
            validity_status="VALID",
            document_version_id=ver_contract.id,
            signer_id=user_ceo.id
        )
        db.add(sig_corp)
        db.flush()

        db.commit()

        # -------------------------------------------------------------
        # 4. Generate Tamper-Evident Audit Ledger Blocks
        # -------------------------------------------------------------
        print("Recording initial hash-chained audit provenance ledger...")
        AuditService.record(db, ActionType.LOGIN.value, ResourceType.USER.value, user_sp.id, user_sp, details={"ip": "10.0.1.20", "auth_method": "Biometric + Credential"})
        AuditService.record(db, ActionType.WRITE.value, ResourceType.WORKSPACE.value, ws_police_case.id, user_sp, details={"workspace": ws_police_case.code})
        AuditService.record(db, ActionType.WRITE.value, ResourceType.DOCUMENT.value, doc_fir.id, user_si, details={"title": doc_fir.title, "sha256": fir_hash})
        AuditService.record(db, ActionType.WRITE.value, ResourceType.DOCUMENT.value, doc_bal.id, user_sp, details={"title": doc_bal.title, "sha256": bal_hash})
        AuditService.record(db, ActionType.APPROVE.value, ResourceType.DOCUMENT_VERSION.value, ver_bal.id, user_sp, details={"version": 1})
        AuditService.record(db, ActionType.SIGN.value, ResourceType.SIGNATURE.value, sig_bal.id, user_sp, details={"algorithm": "RSA-PSS-SHA256", "signed_hash": bal_hash})

        AuditService.record(db, ActionType.LOGIN.value, ResourceType.USER.value, user_judge.id, user_judge, details={"ip": "10.0.2.14", "auth_method": "Judicial Token"})
        AuditService.record(db, ActionType.WRITE.value, ResourceType.DOCUMENT.value, doc_order.id, user_judge, details={"title": doc_order.title, "sha256": order_hash})
        AuditService.record(db, ActionType.APPROVE.value, ResourceType.DOCUMENT_VERSION.value, ver_order.id, user_judge, details={"version": 1})
        AuditService.record(db, ActionType.SIGN.value, ResourceType.SIGNATURE.value, sig_order.id, user_judge, details={"algorithm": "RSA-PSS-SHA256", "signed_hash": order_hash})

        AuditService.record(db, ActionType.LOGIN.value, ResourceType.USER.value, user_ceo.id, user_ceo, details={"ip": "192.168.1.5", "auth_method": "Corporate SSO"})
        AuditService.record(db, ActionType.SIGN.value, ResourceType.SIGNATURE.value, sig_corp.id, user_ceo, details={"algorithm": "RSA-PSS-SHA256", "signed_hash": corp_hash})

        # Verify initial ledger
        verify = AuditService.verify_ledger_integrity(db)
        print(f"Audit ledger integrity verified: {verify['is_valid']} ({verify['total_records']} blocks linked).")
        print("Database seed completed successfully!")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
