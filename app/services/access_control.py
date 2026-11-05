"""Access Control & Clearance Engine: Dynamic multi-tier policy enforcement."""
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.constants import ClassificationLevel, ActionType, ResourceType
from app.models.user import User
from app.models.workspace import Workspace
from app.models.document import Document
from app.services.audit_service import AuditService


class SecurityViolationException(HTTPException):
    def __init__(self, detail: str, code: str = "CLEARANCE_INSUFFICIENT"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Access Denied", "reason": detail, "code": code}
        )


class AccessControlService:
    @classmethod
    def get_effective_clearance(cls, user: User) -> ClassificationLevel:
        """Determines the user's effective clearance (bounded by position limit)."""
        user_rank = ClassificationLevel.get_rank(user.clearance_level)
        if user.position and user.position.max_clearance:
            pos_rank = ClassificationLevel.get_rank(user.position.max_clearance)
            effective_rank = min(user_rank, pos_rank)
        else:
            effective_rank = user_rank

        for level in ClassificationLevel:
            if ClassificationLevel.get_rank(level) == effective_rank:
                return level
        return ClassificationLevel.UNCLASSIFIED

    @classmethod
    def can_perform_action(cls, user: User, action: str) -> bool:
        """Validates if user's position allows the given action type."""
        if user.is_admin:
            return True
        if not user.position:
            return action == ActionType.READ.value
        
        # Check explicit position flags
        if action == ActionType.SIGN.value and not user.position.can_sign:
            return False
        if action == ActionType.APPROVE.value and not user.position.can_approve:
            return False
        if action == ActionType.EXPORT.value and not user.position.can_export:
            return False

        allowed = user.position.allowed_actions
        return action in allowed or "*" in allowed

    @classmethod
    def authorize_workspace(
        cls,
        db: Session,
        user: User,
        workspace: Workspace,
        action: str,
        record_audit: bool = True
    ) -> bool:
        """Evaluates whether the user may access the specified workspace."""
        # 1. Organization tenant isolation
        if user.organization_id != workspace.organization_id and not user.is_admin:
            cls._reject_and_audit(
                db, user, action, ResourceType.WORKSPACE.value, workspace.id,
                f"Cross-organization access rejected: user org {user.organization_id} vs workspace org {workspace.organization_id}",
                "CROSS_TENANT_VIOLATION", record_audit
            )

        # 2. Workspace security clearance
        effective_clearance = cls.get_effective_clearance(user)
        if not ClassificationLevel.can_access(effective_clearance, workspace.classification):
            cls._reject_and_audit(
                db, user, action, ResourceType.WORKSPACE.value, workspace.id,
                f"Insufficient clearance: User has {effective_clearance.value}, workspace requires {workspace.classification}",
                "CLEARANCE_INSUFFICIENT", record_audit
            )

        # 3. Position capabilities
        if not cls.can_perform_action(user, action):
            cls._reject_and_audit(
                db, user, action, ResourceType.WORKSPACE.value, workspace.id,
                f"Position '{user.position.title if user.position else 'None'}' does not hold '{action}' privileges",
                "POSITION_PRIVILEGE_MISSING", record_audit
            )

        return True

    @classmethod
    def authorize_document(
        cls,
        db: Session,
        user: User,
        document: Document,
        action: str,
        record_audit: bool = True
    ) -> bool:
        """Evaluates whether this person, in this position, may see or change this document."""
        # Check workspace first
        cls.authorize_workspace(db, user, document.workspace, action, record_audit=False)

        # Document-specific classification check
        effective_clearance = cls.get_effective_clearance(user)
        if not ClassificationLevel.can_access(effective_clearance, document.classification):
            cls._reject_and_audit(
                db, user, action, ResourceType.DOCUMENT.value, document.id,
                f"Document clearance violation: Document is classified '{document.classification}', "
                f"but {user.full_name} ({user.position.title if user.position else 'Staff'}) holds '{effective_clearance.value}' clearance.",
                "CLASSIFICATION_BREACH", record_audit
            )

        # Specific action check
        if not cls.can_perform_action(user, action):
            cls._reject_and_audit(
                db, user, action, ResourceType.DOCUMENT.value, document.id,
                f"Action '{action}' is not authorized for position '{user.position.title if user.position else 'Standard User'}'.",
                "POSITION_ACTION_UNAUTHORIZED", record_audit
            )

        return True

    @classmethod
    def _reject_and_audit(
        cls,
        db: Session,
        user: User,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        reason: str,
        code: str,
        record_audit: bool
    ):
        """Logs security access denial in the tamper-evident ledger and raises exception."""
        if record_audit:
            AuditService.record(
                db=db,
                action=ActionType.ACCESS_DENIED.value,
                resource_type=resource_type,
                resource_id=resource_id,
                actor=user,
                status="DENIED",
                details={
                    "attempted_action": action,
                    "reason": reason,
                    "violation_code": code,
                    "user_clearance": user.clearance_level,
                    "user_position": user.position.title if user.position else None
                }
            )
        raise SecurityViolationException(detail=reason, code=code)
