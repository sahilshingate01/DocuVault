"""Advanced Document Search API with clearance filtering and SHA-256 reverse lookup."""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.constants import ActionType, ResourceType, ClassificationLevel
from app.models.user import User
from app.models.workspace import Workspace
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.schemas.search import SearchResponse
from app.schemas.document import DocumentResponse, DocumentVersionResponse
from app.api.deps import get_current_user
from app.services.access_control import AccessControlService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=SearchResponse)
def search_documents(
    q: Optional[str] = Query(None, description="Free text query matching title, document number, description, or tags"),
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
    classification: Optional[str] = Query(None, description="Filter by classification level"),
    status: Optional[str] = Query(None, description="Filter by document status (e.g. APPROVED, SIGNED)"),
    sha256: Optional[str] = Query(None, description="Reverse lookup by exact SHA-256 fingerprint"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search documents across workspaces with dynamic clearance-tier access control.
    Any documents exceeding the user's security clearance are strictly omitted.
    """
    effective_clearance = AccessControlService.get_effective_clearance(current_user)

    query = db.query(Document).join(Workspace).filter(
        Workspace.organization_id == current_user.organization_id
    )

    if workspace_id:
        query = query.filter(Document.workspace_id == workspace_id)

    if status:
        query = query.filter(Document.status == status)

    if classification:
        query = query.filter(Document.classification == classification)

    if sha256:
        query = query.join(DocumentVersion).filter(DocumentVersion.sha256_hash.ilike(f"%{sha256}%"))

    if q:
        search_pattern = f"%{q}%"
        query = query.filter(
            or_(
                Document.title.ilike(search_pattern),
                Document.document_number.ilike(search_pattern),
                Document.description.ilike(search_pattern),
                Document._tags.ilike(search_pattern)
            )
        )

    candidates: List[Document] = query.all()

    # Filter out any candidates where clearance is insufficient
    accessible_docs: List[DocumentResponse] = []
    for doc in candidates:
        if ClassificationLevel.can_access(effective_clearance, doc.classification) and \
           ClassificationLevel.can_access(effective_clearance, doc.workspace.classification):
            res = DocumentResponse.model_validate(doc)
            if doc.versions:
                res.current_version = DocumentVersionResponse.model_validate(doc.versions[0])
            accessible_docs.append(res)

    AuditService.record(
        db=db,
        action="SEARCH",
        resource_type=ResourceType.DOCUMENT.value,
        actor=current_user,
        details={
            "query": q,
            "sha256_filter": sha256,
            "total_matches": len(accessible_docs),
            "user_clearance": effective_clearance.value
        }
    )

    return SearchResponse(
        total_matches=len(accessible_docs),
        query=q or sha256 or "",
        results=accessible_docs
    )
