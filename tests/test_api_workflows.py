"""End-to-end API integration tests for document upload, signing, and audit tracking."""
import io


def test_auth_and_profile_endpoint(client, setup_test_hierarchy):
    resp = client.post("/api/v1/auth/login", json={
        "email": "sp@police.gov.in",
        "password": "Password123!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["user"]["clearance_level"] == "TOP_SECRET"


def test_workspace_and_document_workflow(client, setup_test_hierarchy):
    token_sp = setup_test_hierarchy["token_sp"]
    token_clerk = setup_test_hierarchy["token_clerk"]
    headers_sp = {"Authorization": f"Bearer {token_sp}"}
    headers_clerk = {"Authorization": f"Bearer {token_clerk}"}

    # 1. Create Workspace
    ws_resp = client.post("/api/v1/workspaces", json={
        "name": "Homicide Investigation 2026",
        "code": "CASE-HOM-2026",
        "classification": "CONFIDENTIAL"
    }, headers=headers_sp)
    assert ws_resp.status_code == 201
    workspace_id = ws_resp.json()["id"]

    # 2. Upload Document with file bytes (computes SHA-256 fingerprint)
    file_bytes = b"Autopsy & Ballistics Forensic Evidence"
    doc_resp = client.post("/api/v1/documents/upload", data={
        "title": "Forensic Ballistics Report",
        "document_number": "DOC-BAL-402",
        "workspace_id": workspace_id,
        "classification": "CONFIDENTIAL"
    }, files={
        "file": ("ballistics.txt", io.BytesIO(file_bytes), "text/plain")
    }, headers=headers_sp)

    assert doc_resp.status_code == 201
    doc_data = doc_resp.json()
    doc_id = doc_data["id"]
    version_id = doc_data["current_version"]["id"]
    sha256_hash = doc_data["current_version"]["sha256_hash"]
    assert len(sha256_hash) == 64

    # 3. Clerk (RESTRICTED) attempts to access CONFIDENTIAL document -> 403 Forbidden!
    forbidden_resp = client.get(f"/api/v1/documents/{doc_id}", headers=headers_clerk)
    assert forbidden_resp.status_code == 403

    # 4. Formally Approve the version
    approve_resp = client.post(f"/api/v1/signatures/approve/{version_id}", headers=headers_sp)
    assert approve_resp.status_code == 200

    # 5. Digitally Sign the approved version with RSA-PSS key
    sign_resp = client.post(f"/api/v1/signatures/sign/{version_id}", json={
        "reason": "Official forensic verification"
    }, headers=headers_sp)
    assert sign_resp.status_code == 200
    sig_id = sign_resp.json()["id"]

    # 6. Verify Digital Signature mathematically
    verify_resp = client.get(f"/api/v1/signatures/verify/{sig_id}", headers=headers_sp)
    assert verify_resp.status_code == 200
    assert verify_resp.json()["is_valid"] is True

    # 7. Download and verify integrity
    download_resp = client.get(f"/api/v1/documents/{doc_id}/versions/1/download", headers=headers_sp)
    assert download_resp.status_code == 200
    assert download_resp.content == file_bytes

    # 8. Check that tamper-evident audit ledger contains events
    audit_resp = client.get("/api/v1/audit/logs", headers=headers_sp)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert len(logs) >= 5

    # 9. Verify ledger integrity
    verify_ledger = client.get("/api/v1/audit/verify", headers=headers_sp)
    assert verify_ledger.status_code == 200
    assert verify_ledger.json()["is_valid"] is True


def test_document_integrity_verification_and_tamper_detection(
    client, setup_test_hierarchy, db_session
):
    """The integrity API accepts an unchanged file and flags modified bytes."""
    from app.models.document_version import DocumentVersion

    token = setup_test_hierarchy["token_sp"]
    headers = {"Authorization": f"Bearer {token}"}

    workspace_response = client.post(
        "/api/v1/workspaces",
        json={"name": "Integrity Test", "code": "CASE-INTEGRITY-1"},
        headers=headers,
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]

    original_bytes = b"Original case report"
    upload_response = client.post(
        "/api/v1/documents/upload",
        data={
            "title": "Integrity Report",
            "document_number": "DOC-INTEGRITY-1",
            "workspace_id": workspace_id,
        },
        files={"file": ("report.txt", original_bytes, "text/plain")},
        headers=headers,
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["id"]

    verify_url = f"/api/v1/documents/{document_id}/versions/1/verify"
    intact_response = client.get(verify_url, headers=headers)
    assert intact_response.status_code == 200
    assert intact_response.json()["is_intact"] is True

    version = db_session.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id,
        DocumentVersion.version_number == 1,
    ).one()
    with open(version.file_path, "wb") as stored_file:
        stored_file.write(b"Modified case report")

    tampered_response = client.get(verify_url, headers=headers)
    assert tampered_response.status_code == 200
    assert tampered_response.json()["is_intact"] is False
    assert tampered_response.json()["stored_sha256"] != tampered_response.json()["calculated_sha256"]


def test_upload_rejects_files_larger_than_limit(client, setup_test_hierarchy):
    from app.services.storage_service import StorageService

    token = setup_test_hierarchy["token_sp"]
    headers = {"Authorization": f"Bearer {token}"}
    workspace_response = client.post(
        "/api/v1/workspaces",
        json={"name": "Size Test", "code": "CASE-SIZE-1"},
        headers=headers,
    )
    assert workspace_response.status_code == 201

    too_large = b"x" * (StorageService.MAX_UPLOAD_SIZE + 1)
    response = client.post(
        "/api/v1/documents/upload",
        data={
            "title": "Oversized Report",
            "document_number": "DOC-OVERSIZE-1",
            "workspace_id": workspace_response.json()["id"],
        },
        files={"file": ("large.txt", too_large, "text/plain")},
        headers=headers,
    )
    assert response.status_code == 413
