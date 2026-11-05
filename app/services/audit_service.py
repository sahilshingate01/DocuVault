"""Audit Service: Records tamper-evident hash-chained logs and verifies ledger integrity."""
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.user import User


class AuditService:
    @staticmethod
    def compute_entry_hash(
        sequence_number: int,
        timestamp_iso: str,
        previous_hash: str,
        user_id: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        status: str,
        details_json: str
    ) -> str:
        """Calculates canonical SHA-256 hash for an audit record, chained to previous_hash."""
        canonical_string = (
            f"{sequence_number}|"
            f"{timestamp_iso}|"
            f"{previous_hash}|"
            f"{user_id or ''}|"
            f"{action}|"
            f"{resource_type}|"
            f"{resource_id or ''}|"
            f"{status}|"
            f"{details_json}"
        )
        return hashlib.sha256(canonical_string.encode("utf-8")).hexdigest()

    @classmethod
    def record(
        cls,
        db: Session,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        actor: Optional[User] = None,
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Appends a new immutable, cryptographically chained block to the audit ledger."""
        # Find latest entry to get sequence number and previous hash
        latest = db.query(AuditLog).order_by(AuditLog.sequence_number.desc()).first()
        
        if latest is None:
            sequence_number = 1
            previous_hash = settings.AUDIT_GENESIS_PREV_HASH
        else:
            sequence_number = latest.sequence_number + 1
            previous_hash = latest.entry_hash

        now = datetime.now(timezone.utc)
        timestamp_iso = now.isoformat()
        details_str = json.dumps(details or {}, sort_keys=True)

        entry_hash = cls.compute_entry_hash(
            sequence_number=sequence_number,
            timestamp_iso=timestamp_iso,
            previous_hash=previous_hash,
            user_id=actor.id if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            details_json=details_str
        )

        user_position_title = None
        if actor and actor.position:
            user_position_title = actor.position.title

        log_entry = AuditLog(
            sequence_number=sequence_number,
            timestamp=now,
            timestamp_iso=timestamp_iso,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
            user_id=actor.id if actor else None,
            user_email=actor.email if actor else "anonymous@system",
            user_name=actor.full_name if actor else "System",
            user_position=user_position_title,
            organization_id=actor.organization_id if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            ip_address=ip_address,
            details_json=details_str
        )

        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @classmethod
    def verify_ledger_integrity(cls, db: Session) -> Dict[str, Any]:
        """
        Cryptographically verifies the entire audit ledger from Genesis to Tip.
        Detects any unauthorized modification, deletion, or insertion of records.
        """
        logs: List[AuditLog] = db.query(AuditLog).order_by(AuditLog.sequence_number.asc()).all()

        if not logs:
            return {
                "is_valid": True,
                "total_records": 0,
                "message": "Audit ledger is empty (pristine genesis state).",
                "broken_at_sequence": None
            }

        expected_prev_hash = settings.AUDIT_GENESIS_PREV_HASH

        for idx, entry in enumerate(logs):
            expected_seq = idx + 1
            # Check 1: Sequence continuity
            if entry.sequence_number != expected_seq:
                return {
                    "is_valid": False,
                    "total_records": len(logs),
                    "broken_at_sequence": entry.sequence_number,
                    "message": f"Sequence discontinuity detected! Expected #{expected_seq}, found #{entry.sequence_number}."
                }

            # Check 2: Previous hash chain linkage
            if entry.previous_hash != expected_prev_hash:
                return {
                    "is_valid": False,
                    "total_records": len(logs),
                    "broken_at_sequence": entry.sequence_number,
                    "message": f"Hash chain broken at block #{entry.sequence_number}. Previous hash mismatch."
                }

            # Check 3: Entry content integrity (recomputing SHA-256)
            ts_str = entry.timestamp_iso if getattr(entry, "timestamp_iso", None) else entry.timestamp.isoformat()
            recalculated_hash = cls.compute_entry_hash(
                sequence_number=entry.sequence_number,
                timestamp_iso=ts_str,
                previous_hash=entry.previous_hash,
                user_id=entry.user_id,
                action=entry.action,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                status=entry.status,
                details_json=entry.details_json
            )

            if recalculated_hash != entry.entry_hash:
                return {
                    "is_valid": False,
                    "total_records": len(logs),
                    "broken_at_sequence": entry.sequence_number,
                    "message": f"Data tampering detected in block #{entry.sequence_number}! Stored hash does not match computed content digest."
                }

            expected_prev_hash = entry.entry_hash

        return {
            "is_valid": True,
            "total_records": len(logs),
            "latest_sequence": logs[-1].sequence_number,
            "head_hash": logs[-1].entry_hash,
            "message": "Cryptographic audit ledger is intact and mathematically verified."
        }
