"""Access Control & Clearance Engine: Dynamic multi-tier ABAC policy enforcement."""
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.constants import ClassificationLevel, ActionType, ResourceType, DocumentStatus
from app.models.user import User
from app.models.workspace import Workspace
from app.models.document import Document
from app.models.temporary_clearance import TemporaryClearance
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
    def has_clearance(
        cls,
        db: Session,
        user: User,
        target_classification: str,
        workspace_id: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> bool:
        """Checks if user has required clearance either permanently or via active temporary grant."""
        effective_clearance = cls.get_effective_clearance(user)
        if ClassificationLevel.can_access(effective_clearance, target_classification):
            return True

        # Check temporary clearance grants
        now = datetime.now(timezone.utc)
        temp_grants = db.query(TemporaryClearance).filter(
            TemporaryClearance.user_id == user.id,
            TemporaryClearance.is_revoked == False,
            TemporaryClearance.valid_from <= now,
            TemporaryClearance.valid_until >= now
        ).all()

        for grant in temp_grants:
            matches_scope = False
            if grant.document_id and document_id and grant.document_id == document_id:
                matches_scope = True
            elif grant.workspace_id and workspace_id and grant.workspace_id == workspace_id:
                matches_scope = True
            elif not grant.workspace_id and not grant.document_id:
                matches_scope = True

            if matches_scope and ClassificationLevel.can_access(grant.granted_clearance, target_classification):
                return True

        return False

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
    def evaluate_abac_policy(
        cls,
        db: Session,
        user: User,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive Attribute-Based Access Control (ABAC) evaluation engine.
        Evaluates Subject, Resource, Action, and Environment context attributes.
        Returns explicit Allow/Deny decision with full rule trace.
        """
        now = datetime.now(timezone.utc)
        rules_evaluated: List[Dict[str, Any]] = []

        subject_attrs = {
            "user_id": user.id,
            "email": user.email,
            "organization_id": user.organization_id,
            "department_id": user.department_id,
            "position": user.position.title if user.position else None,
            "designation_type": getattr(user.position, "designation_type", None) if user.position else None,
            "clearance_level": user.clearance_level,
            "effective_clearance": cls.get_effective_clearance(user).value,
            "is_admin": user.is_admin,
            "is_active": user.is_active
        }

        # 1. Rule: User active check
        rule_active = {
            "rule": "SUBJECT_ACTIVE_CHECK",
            "passed": user.is_active,
            "details": "User account must be active"
        }
        rules_evaluated.append(rule_active)
        if not user.is_active:
            return {
                "decision": "DENY",
                "allowed": False,
                "denial_reason": "User account is deactivated.",
                "code": "USER_INACTIVE",
                "subject_attributes": subject_attrs,
                "evaluated_policies": rules_evaluated
            }

        # Superadmin bypass for global administration
        if user.is_admin and action in [ActionType.READ.value, ActionType.WRITE.value, ActionType.UPDATE.value]:
            rules_evaluated.append({
                "rule": "ADMIN_OVERRIDE",
                "passed": True,
                "details": "System administrator bypass"
            })
            return {
                "decision": "ALLOW",
                "allowed": True,
                "denial_reason": None,
                "code": "ADMIN_PERMITTED",
                "subject_attributes": subject_attrs,
                "evaluated_policies": rules_evaluated
            }

        # 2. Rule: Position action capability
        can_act = cls.can_perform_action(user, action)
        rule_position = {
            "rule": "POSITION_ACTION_CAPABILITY",
            "passed": can_act,
            "details": f"Position allows action '{action}'"
        }
        rules_evaluated.append(rule_position)
        if not can_act:
            return {
                "decision": "DENY",
                "allowed": False,
                "denial_reason": f"Position '{user.position.title if user.position else 'Staff'}' lacks authority for action '{action}'.",
                "code": "POSITION_ACTION_UNAUTHORIZED",
                "subject_attributes": subject_attrs,
                "evaluated_policies": rules_evaluated
            }

        # Resolve Target Resource Attributes
        resource_attrs: Dict[str, Any] = {"type": resource_type, "id": resource_id}
        target_classification = ClassificationLevel.UNCLASSIFIED.value
        res_org_id = user.organization_id
        res_dept_id = None
        is_closed_or_archived = False

        if resource_type == ResourceType.WORKSPACE.value and resource_id:
            ws = db.query(Workspace).filter(Workspace.id == resource_id).first()
            if ws:
                res_org_id = ws.organization_id
                res_dept_id = ws.department_id
                target_classification = ws.classification
                is_closed_or_archived = ws.is_closed
                resource_attrs.update({
                    "name": ws.name,
                    "code": ws.code,
                    "organization_id": ws.organization_id,
                    "department_id": ws.department_id,
                    "classification": ws.classification,
                    "is_closed": ws.is_closed
                })

        elif resource_type == ResourceType.DOCUMENT.value and resource_id:
            doc = db.query(Document).filter(Document.id == resource_id).first()
            if doc:
                res_org_id = doc.workspace.organization_id if doc.workspace else user.organization_id
                res_dept_id = doc.workspace.department_id if doc.workspace else None
                target_classification = doc.classification
                is_closed_or_archived = (doc.status == DocumentStatus.ARCHIVED.value or doc.is_deleted)
                resource_attrs.update({
                    "title": doc.title,
                    "document_number": doc.document_number,
                    "classification": doc.classification,
                    "status": doc.status,
                    "workspace_id": doc.workspace_id,
                    "is_deleted": doc.is_deleted
                })

        # 3. Rule: Organization boundary isolation
        org_match = (user.organization_id == res_org_id) or user.is_admin
        rule_tenant = {
            "rule": "ORGANIZATION_TENANT_ISOLATION",
            "passed": org_match,
            "details": f"User org {user.organization_id} matches resource org {res_org_id}"
        }
        rules_evaluated.append(rule_tenant)
        if not org_match:
            return {
                "decision": "DENY",
                "allowed": False,
                "denial_reason": "Cross-organization access is strictly forbidden by multi-tenant boundary policy.",
                "code": "CROSS_TENANT_VIOLATION",
                "subject_attributes": subject_attrs,
                "resource_attributes": resource_attrs,
                "evaluated_policies": rules_evaluated
            }

        # 3b. Rule: Department boundary isolation for mutations
        designation = (getattr(user.position, "designation_type", None) or "").upper()
        is_executive = designation in ["SP", "JUDGE", "CEO", "DIRECTOR"] or user.is_admin
        dept_match = True
        if res_dept_id and user.department_id and res_dept_id != user.department_id:
            # Cross-department writes/updates are restricted to executive designations (SP, Judge, CEO) or admins
            if action in [ActionType.WRITE.value, ActionType.UPDATE.value, ActionType.DELETE.value, ActionType.APPROVE.value]:
                dept_match = is_executive

        rule_dept = {
            "rule": "DEPARTMENT_BOUNDARY_POLICY",
            "passed": dept_match,
            "details": f"User dept {user.department_id} vs resource dept {res_dept_id} (Executive override: {is_executive})"
        }
        rules_evaluated.append(rule_dept)
        if not dept_match:
            return {
                "decision": "DENY",
                "allowed": False,
                "denial_reason": "Cross-department modification denied: Department boundary enforcement restricts non-executive users from modifying external department assets.",
                "code": "DEPARTMENT_BOUNDARY_VIOLATION",
                "subject_attributes": subject_attrs,
                "resource_attributes": resource_attrs,
                "evaluated_policies": rules_evaluated
            }

        # 4. Rule: Bell-LaPadula Security Clearance (with Temporary Clearance delegation check)
        clearance_ok = cls.has_clearance(
            db=db,
            user=user,
            target_classification=target_classification,
            workspace_id=resource_id if resource_type == ResourceType.WORKSPACE.value else None,
            document_id=resource_id if resource_type == ResourceType.DOCUMENT.value else None
        )
        rule_clearance = {
            "rule": "SECURITY_CLEARANCE_POLICY",
            "passed": clearance_ok,
            "details": f"User clearance ({cls.get_effective_clearance(user).value}) meets required level ({target_classification})"
        }
        rules_evaluated.append(rule_clearance)
        if not clearance_ok:
            return {
                "decision": "DENY",
                "allowed": False,
                "denial_reason": f"Clearance breach: Required classification is '{target_classification}', user holds '{cls.get_effective_clearance(user).value}'.",
                "code": "CLEARANCE_INSUFFICIENT",
                "subject_attributes": subject_attrs,
                "resource_attributes": resource_attrs,
                "evaluated_policies": rules_evaluated
            }

        # 5. Rule: Archival / Closed Resource Mutation Check
        if is_closed_or_archived and action in [ActionType.WRITE.value, ActionType.UPDATE.value, ActionType.SIGN.value]:
            rule_archival = {
                "rule": "IMMUTABLE_LIFECYCLE_PROTECTION",
                "passed": False,
                "details": "Resource is closed or archived; mutations prohibited"
            }
            rules_evaluated.append(rule_archival)
            return {
                "decision": "DENY",
                "allowed": False,
                "denial_reason": "Cannot modify or sign a closed or archived resource.",
                "code": "RESOURCE_SEALED",
                "subject_attributes": subject_attrs,
                "resource_attributes": resource_attrs,
                "evaluated_policies": rules_evaluated
            }

        return {
            "decision": "ALLOW",
            "allowed": True,
            "denial_reason": None,
            "code": "ACCESS_GRANTED",
            "subject_attributes": subject_attrs,
            "resource_attributes": resource_attrs,
            "evaluated_policies": rules_evaluated
        }

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
        eval_result = cls.evaluate_abac_policy(
            db=db,
            user=user,
            action=action,
            resource_type=ResourceType.WORKSPACE.value,
            resource_id=workspace.id
        )
        if not eval_result["allowed"]:
            cls._reject_and_audit(
                db, user, action, ResourceType.WORKSPACE.value, workspace.id,
                eval_result["denial_reason"], eval_result["code"], record_audit
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
        """Evaluates whether this person, in this position, may access or alter this document."""
        eval_result = cls.evaluate_abac_policy(
            db=db,
            user=user,
            action=action,
            resource_type=ResourceType.DOCUMENT.value,
            resource_id=document.id
        )
        if not eval_result["allowed"]:
            cls._reject_and_audit(
                db, user, action, ResourceType.DOCUMENT.value, document.id,
                eval_result["denial_reason"], eval_result["code"], record_audit
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
