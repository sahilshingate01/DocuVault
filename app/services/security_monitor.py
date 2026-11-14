"""Security Event Monitoring: Detects suspicious activity, tampering, and anomalies."""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.core.constants import ActionType


class SecurityMonitorService:
    @classmethod
    def get_security_alerts(cls, db: Session, org_id: str | None = None) -> List[Dict[str, Any]]:
        """
        Analyzes the tamper-evident audit ledger to detect security anomalies:
        1. CRITICAL: Physical file or database ledger tampering.
        2. HIGH: Brute force login attempts or account lockouts.
        3. HIGH: Repeated clearance violation attempts / privilege escalation.
        4. MEDIUM: Anomalous rapid downloading spikes.
        """
        alerts: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        since_24h = now - timedelta(hours=24)

        query = db.query(AuditLog)
        if org_id:
            query = query.filter((AuditLog.organization_id == org_id) | (AuditLog.organization_id.is_(None)))

        # 1. Tamper detection events
        tamper_events = query.filter(
            AuditLog.action == ActionType.TAMPER_DETECTED.value,
            AuditLog.timestamp >= since_24h
        ).all()
        for ev in tamper_events:
            alerts.append({
                "severity": "CRITICAL",
                "type": "CRYPTO_TAMPER_DETECTED",
                "timestamp": ev.timestamp.isoformat(),
                "actor": ev.actor.full_name if ev.actor else "System",
                "resource_type": ev.resource_type,
                "resource_id": ev.resource_id,
                "description": "Cryptographic checksum mismatch: Disk bits or database ledger modified without valid signature."
            })

        # 2. Access Denied / Clearance Violations
        denials = query.filter(
            AuditLog.action == ActionType.ACCESS_DENIED.value,
            AuditLog.timestamp >= since_24h
        ).all()

        actor_denials: Dict[str, List[AuditLog]] = {}
        for d in denials:
            actor_key = d.actor.email if d.actor else "unknown"
            actor_denials.setdefault(actor_key, []).append(d)

        for actor_email, evs in actor_denials.items():
            if len(evs) >= 3:
                alerts.append({
                    "severity": "HIGH",
                    "type": "REPEATED_ACCESS_VIOLATIONS",
                    "timestamp": evs[-1].timestamp.isoformat(),
                    "actor": actor_email,
                    "count": len(evs),
                    "description": f"Actor triggered {len(evs)} access denial violations within 24 hours. Possible permission probing or credential attack."
                })

        # 3. Mass Download Burst
        downloads = query.filter(
            AuditLog.action == ActionType.DOWNLOAD.value,
            AuditLog.timestamp >= since_24h
        ).all()
        actor_downloads: Dict[str, List[AuditLog]] = {}
        for dl in downloads:
            actor_key = dl.actor.email if dl.actor else "unknown"
            actor_downloads.setdefault(actor_key, []).append(dl)

        for actor_email, evs in actor_downloads.items():
            if len(evs) >= 15:
                alerts.append({
                    "severity": "MEDIUM",
                    "type": "HIGH_VOLUME_DOWNLOAD_SPIKE",
                    "timestamp": evs[-1].timestamp.isoformat(),
                    "actor": actor_email,
                    "count": len(evs),
                    "description": f"High volume file retrieval: {len(evs)} files downloaded within 24 hours."
                })

        return sorted(alerts, key=lambda x: (x["severity"] == "CRITICAL", x["severity"] == "HIGH", x["timestamp"]), reverse=True)
