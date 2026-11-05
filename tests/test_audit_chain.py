"""Tests for tamper-evident hash-chained audit logging and verification."""
from app.services.audit_service import AuditService
from app.models.audit_log import AuditLog


def test_audit_hash_chain_linkage(db_session, setup_test_hierarchy):
    sp = setup_test_hierarchy["sp"]

    # Block 1
    b1 = AuditService.record(
        db=db_session,
        action="LOGIN",
        resource_type="USER",
        resource_id=sp.id,
        actor=sp
    )
    assert b1.sequence_number == 1
    assert b1.previous_hash == "0" * 64

    # Block 2
    b2 = AuditService.record(
        db=db_session,
        action="READ",
        resource_type="DOCUMENT",
        resource_id="doc-123",
        actor=sp
    )
    assert b2.sequence_number == 2
    assert b2.previous_hash == b1.entry_hash

    # Block 3
    b3 = AuditService.record(
        db=db_session,
        action="SIGN",
        resource_type="SIGNATURE",
        resource_id="sig-456",
        actor=sp
    )
    assert b3.sequence_number == 3
    assert b3.previous_hash == b2.entry_hash

    # Ledger must verify as intact
    report = AuditService.verify_ledger_integrity(db_session)
    assert report["is_valid"] is True
    assert report["total_records"] == 3


def test_tampering_detection(db_session, setup_test_hierarchy):
    sp = setup_test_hierarchy["sp"]

    AuditService.record(db_session, "LOGIN", "USER", sp.id, sp)
    b2 = AuditService.record(db_session, "READ", "DOCUMENT", "doc-1", sp)
    AuditService.record(db_session, "SIGN", "DOCUMENT", "doc-1", sp)

    # Simulate direct unauthorized DB modification by altering block 2's payload
    target = db_session.query(AuditLog).filter(AuditLog.sequence_number == 2).first()
    target.details_json = '{"tampered": true}'
    db_session.commit()

    # Verification must catch the tampering and flag block #2
    report = AuditService.verify_ledger_integrity(db_session)
    assert report["is_valid"] is False
    assert report["broken_at_sequence"] == 2
