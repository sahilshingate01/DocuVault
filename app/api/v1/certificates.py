"""Certificate Endpoints: Official DigiLocker-style Evidence Receipts and Legal Certificates."""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.certificate import CertificateVerificationResponse
from app.api.deps import get_current_user
from app.services.certificate_service import CertificateService

router = APIRouter(prefix="/certificates", tags=["Certificates & Provenance"])


@router.get("/document/{document_id}", response_model=CertificateVerificationResponse)
def get_document_certificate(
    document_id: str,
    version_number: Optional[int] = Query(None, description="Specific version number, defaults to latest"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generates an official DigiLocker-grade Certificate of Authenticity for a document."""
    return CertificateService.generate_document_certificate(
        db=db,
        document_id=document_id,
        requester=current_user,
        version_number=version_number
    )


@router.get("/document/{document_id}/print", response_class=HTMLResponse)
def get_printable_certificate(
    document_id: str,
    version_number: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Renders a court-admissible, printable legal Certificate of Authenticity."""
    cert = CertificateService.generate_document_certificate(
        db=db,
        document_id=document_id,
        requester=current_user,
        version_number=version_number
    )

    signed_badge = f"<span class='seal-signed'>DIGITALLY SIGNED ({cert['signature_algorithm']})</span>" if cert['is_signed'] else "<span class='seal-unsigned'>FINGERPRINT SEALED</span>"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DocuVault Certificate of Authenticity - {cert['certificate_id']}</title>
    <style>
        body {{ font-family: 'Times New Roman', serif; margin: 40px; color: #111; line-height: 1.6; }}
        .border-box {{ border: 4px double #1e3a8a; padding: 30px; border-radius: 8px; }}
        .header {{ text-align: center; border-bottom: 2px solid #1e3a8a; padding-bottom: 15px; margin-bottom: 25px; }}
        .header h1 {{ font-size: 26px; margin: 0; color: #1e3a8a; letter-spacing: 1px; }}
        .header h2 {{ font-size: 16px; margin: 5px 0 0; color: #555; text-transform: uppercase; }}
        .cert-id {{ font-family: monospace; font-size: 14px; color: #2563eb; font-weight: bold; margin-top: 5px; }}
        .field-group {{ margin-bottom: 15px; }}
        .label {{ font-weight: bold; display: inline-block; width: 220px; }}
        .hash-code {{ font-family: monospace; background: #f3f4f6; padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px; }}
        .declaration {{ margin-top: 25px; padding: 15px; background: #f8fafc; border-left: 4px solid #1e3a8a; font-style: italic; }}
        .footer {{ margin-top: 40px; display: flex; justify-content: space-between; align-items: flex-end; }}
        .seal-signed {{ color: #059669; font-weight: bold; border: 2px solid #059669; padding: 4px 10px; border-radius: 4px; text-transform: uppercase; }}
        .seal-unsigned {{ color: #4b5563; font-weight: bold; border: 2px solid #4b5563; padding: 4px 10px; border-radius: 4px; text-transform: uppercase; }}
    </style>
</head>
<body>
    <div class="border-box">
        <div class="header">
            <h1>CERTIFICATE OF AUTHENTICITY & DIGITAL PROVENANCE</h1>
            <h2>DocuVault Secure Document Management System (DigiLocker Architecture)</h2>
            <div class="cert-id">Certificate ID: {cert['certificate_id']}</div>
        </div>

        <div class="field-group"><span class="label">Document Title:</span> <strong>{cert['document_title']}</strong></div>
        <div class="field-group"><span class="label">Reference / Case Number:</span> <strong>{cert['document_number']}</strong></div>
        <div class="field-group"><span class="label">Version Number:</span> Version {cert['version_number']}</div>
        <div class="field-group"><span class="label">Security Classification:</span> {cert['classification']}</div>
        <div class="field-group"><span class="label">SHA-256 Fingerprint:</span> <span class="hash-code">{cert['sha256_fingerprint']}</span></div>
        <div class="field-group"><span class="label">Audit Ledger Block Height:</span> Block #{cert['audit_block_sequence']} (Hash: {cert['audit_entry_hash'][:16]}...)</div>

        <div class="field-group">
            <span class="label">Cryptographic Seal:</span> {signed_badge}
        </div>
        {f"<div class='field-group'><span class='label'>Authorized Signer:</span> {cert['signer_name']} ({cert['signer_title']}) - Signed on {cert['signed_at']}</div>" if cert['is_signed'] else ""}

        <div class="declaration">
            <strong>Legal Admissibility Clause:</strong><br>
            {cert['legal_admissibility_clause']}
        </div>

        <div class="footer">
            <div>
                <div>Issued: {cert['issued_at'].strftime("%Y-%m-%d %H:%M:%S UTC")}</div>
                <div>Status: <strong>VERIFIED GENUINE</strong></div>
            </div>
            <div style="text-align: right;">
                <div style="font-weight: bold;">Electronic Evidence Registrar</div>
                <div style="font-size: 12px; color: #666;">DocuVault Cryptographic Trust Engine</div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html)
