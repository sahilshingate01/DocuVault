"""Security and Authorization Policy Evaluation Schemas."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class AccessEvaluationRequest(BaseModel):
    action: str  # READ, WRITE, UPDATE, DELETE, DOWNLOAD, APPROVE, SIGN, EXPORT
    resource_type: str  # WORKSPACE, DOCUMENT, DOCUMENT_VERSION
    resource_id: Optional[str] = None
    target_user_id: Optional[str] = None  # Admin can simulate another user's access


class PolicyRuleResult(BaseModel):
    rule: str
    passed: bool
    details: str


class AccessEvaluationResponse(BaseModel):
    decision: str  # ALLOW or DENY
    allowed: bool
    denial_reason: Optional[str] = None
    code: Optional[str] = None
    subject_attributes: Dict[str, Any] = {}
    resource_attributes: Dict[str, Any] = {}
    evaluated_policies: List[Dict[str, Any]] = []


class UserPermissionMatrix(BaseModel):
    user_id: str
    email: str
    clearance_level: str
    effective_clearance: str
    is_admin: bool
    position_title: Optional[str] = None
    designation_type: Optional[str] = None
    can_sign: bool
    can_approve: bool
    can_export: bool
    can_manage_users: bool
    allowed_actions: List[str]
    permitted_classifications: List[str]

