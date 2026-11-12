"""Chain of Custody Endpoints: Evidence transfer, receipt verification, and timeline."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.custody import CustodyTransferRequest, CustodyAcceptRequest, CustodyResponse
from app.api.deps import get_current_user
from app.services.custody_service import CustodyService

router = APIRouter(prefix="/custody", tags=["Chain of Custody"])


@router.post("/transfer", response_model=CustodyResponse, status_code=status.HTTP_201_CREATED)
def initiate_evidence_transfer(
    req: CustodyTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initiates formal legal custody transfer of a document or evidence version.
    Records sender, recipient, tamper seal number, and baseline SHA-256 fingerprint.
    """
    return CustodyService.initiate_transfer(
        db=db,
        sender=current_user,
        receiver_id=req.receiver_id,
        version_id=req.version_id,
        transfer_reason=req.transfer_reason,
        custody_location=req.custody_location,
        tamper_seal_number=req.tamper_seal_number,
        notes=req.notes
    )


@router.post("/{custody_id}/accept", response_model=CustodyResponse)
def accept_evidence_custody(
    custody_id: str,
    req: CustodyAcceptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Receiving officer formally accepts custody after validating seal and SHA-256 fingerprint.
    """
    return CustodyService.accept_custody(
        db=db,
        receiver=current_user,
        custody_id=custody_id,
        verification_notes=req.verification_notes
    )


@router.get("/timeline/{document_id}", response_model=List[CustodyResponse])
def get_document_custody_timeline(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves full chronological legal custody movements for a case file or evidence."""
    return CustodyService.get_document_timeline(db, document_id)
