"""Diff and Version Comparison Endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.diff import DocumentDiffResponse
from app.api.deps import get_current_user
from app.services.diff_service import DiffService

router = APIRouter(prefix="/diff", tags=["Version Diff & Tamper Inspector"])


@router.get("/document/{document_id}", response_model=DocumentDiffResponse)
def compare_document_versions(
    document_id: str,
    v1: int = Query(1, description="Baseline version number (e.g. initial statement)"),
    v2: int = Query(2, description="Target version number (e.g. current statement)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Forensically compares two versions of a document or witness statement.
    Exposes modified text lines, similarity ratio, and tampering assessment.
    """
    return DiffService.compare_versions(
        db=db,
        document_id=document_id,
        v1_num=v1,
        v2_num=v2,
        user=current_user
    )
