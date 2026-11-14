"""Comprehensive Tests for Person 2: Document Vault & Version Management."""
import io
import pytest
from app.models.document import Document
from app.models.document_version import DocumentVersion


def test_document_lifecycle_upload_version_restore(client, setup_test_hierarchy):
    """Tests complete versioning lifecycle: upload v1, upload v2, query history, rollback to v1."""
    headers_sp = {"Authorization": f"Bearer {setup_test_hierarchy['token_sp']}"}

    # 1. Create Workspace
    ws_res = client.post("/api/v1/workspaces", headers=headers_sp, json={
        "name": "Forensic Evidence Locker",
        "code": "WS-FEL-01",
        "classification": "CONFIDENTIAL"
    })
    assert ws_res.status_code == 201
    ws_id = ws_res.json()["id"]

    # 2. Upload Document v1
    file_bytes_v1 = b"INITIAL CRIME SCENE STATEMENT - VERSION 1"
    upload_res = client.post(
        "/api/v1/documents/upload",
        headers=headers_sp,
        data={
            "title": "Crime Scene Statement",
            "document_number": "DOC-STMT-001",
            "workspace_id": ws_id,
            "classification": "CONFIDENTIAL"
        },
        files={"file": ("statement.txt", io.BytesIO(file_bytes_v1), "text/plain")}
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    v1_hash = doc_data["current_version"]["sha256_hash"]

    # 3. Upload Document v2
    file_bytes_v2 = b"UPDATED CRIME SCENE STATEMENT WITH BALLISTICS - VERSION 2"
    v2_res = client.post(
        f"/api/v1/documents/{doc_id}/versions",
        headers=headers_sp,
        data={"change_summary": "Added ballistics analysis note"},
        files={"file": ("statement_v2.txt", io.BytesIO(file_bytes_v2), "text/plain")}
    )
    assert v2_res.status_code == 200
    assert v2_res.json()["current_version"]["version_number"] == 2
    v2_hash = v2_res.json()["current_version"]["sha256_hash"]
    assert v1_hash != v2_hash

    # 4. Query version history
    hist_res = client.get(f"/api/v1/documents/{doc_id}/versions", headers=headers_sp)
    assert hist_res.status_code == 200
    versions = hist_res.json()
    assert len(versions) == 2
    assert versions[0]["version_number"] == 2
    assert versions[1]["version_number"] == 1

    # 5. Restore version 1 as version 3 (Rollback)
    rollback_res = client.post(f"/api/v1/documents/{doc_id}/versions/1/restore", headers=headers_sp)
    assert rollback_res.status_code == 200
    assert rollback_res.json()["current_version"]["version_number"] == 3
    assert rollback_res.json()["current_version"]["sha256_hash"] == v1_hash


def test_file_integrity_verification(client, setup_test_hierarchy):
    """Tests on-demand physical disk SHA-256 integrity verification."""
    headers_sp = {"Authorization": f"Bearer {setup_test_hierarchy['token_sp']}"}

    ws_res = client.post("/api/v1/workspaces", headers=headers_sp, json={
        "name": "Integrity Test Workspace",
        "code": "WS-INT-01",
        "classification": "UNCLASSIFIED"
    })
    ws_id = ws_res.json()["id"]

    upload_res = client.post(
        "/api/v1/documents/upload",
        headers=headers_sp,
        data={
            "title": "Chain Integrity File",
            "document_number": "DOC-INT-001",
            "workspace_id": ws_id,
            "classification": "UNCLASSIFIED"
        },
        files={"file": ("evidence.txt", io.BytesIO(b"UNALTERED DISK BYTES"), "text/plain")}
    )
    doc_id = upload_res.json()["id"]

    # Verify single version integrity
    v_verify = client.get(f"/api/v1/documents/{doc_id}/versions/1/verify", headers=headers_sp)
    assert v_verify.status_code == 200
    assert v_verify.json()["is_intact"] is True

    # Verify complete document integrity across all versions
    all_verify = client.get(f"/api/v1/documents/{doc_id}/verify", headers=headers_sp)
    assert all_verify.status_code == 200
    assert all_verify.json()["all_versions_intact"] is True


def test_document_download_and_sha256_header(client, setup_test_hierarchy):
    """Tests file download API, ensuring X-Vault-SHA256 headers are returned."""
    headers_sp = {"Authorization": f"Bearer {setup_test_hierarchy['token_sp']}"}

    ws_res = client.post("/api/v1/workspaces", headers=headers_sp, json={
        "name": "Download Test Workspace",
        "code": "WS-DL-01",
        "classification": "UNCLASSIFIED"
    })
    ws_id = ws_res.json()["id"]

    raw_bytes = b"CONFIDENTIAL DISCOVERY EVIDENCE STREAM"
    upload_res = client.post(
        "/api/v1/documents/upload",
        headers=headers_sp,
        data={
            "title": "Streamed Discovery Document",
            "document_number": "DOC-STREAM-001",
            "workspace_id": ws_id,
            "classification": "UNCLASSIFIED"
        },
        files={"file": ("stream.txt", io.BytesIO(raw_bytes), "text/plain")}
    )
    doc_id = upload_res.json()["id"]
    expected_hash = upload_res.json()["current_version"]["sha256_hash"]

    # Download latest
    dl_res = client.get(f"/api/v1/documents/{doc_id}/download", headers=headers_sp)
    assert dl_res.status_code == 200
    assert dl_res.content == raw_bytes
    assert dl_res.headers.get("x-vault-sha256") == expected_hash


def test_document_archival_and_trash_lifecycle(client, setup_test_hierarchy):
    """Tests archival, unarchival, soft-deletion to trash, and trash restoration."""
    headers_sp = {"Authorization": f"Bearer {setup_test_hierarchy['token_sp']}"}

    ws_res = client.post("/api/v1/workspaces", headers=headers_sp, json={
        "name": "Lifecycle Workspace",
        "code": "WS-LIFE-01",
        "classification": "UNCLASSIFIED"
    })
    ws_id = ws_res.json()["id"]

    upload_res = client.post(
        "/api/v1/documents/upload",
        headers=headers_sp,
        data={
            "title": "Lifecycle Governed Document",
            "document_number": "DOC-LIFE-001",
            "workspace_id": ws_id,
            "classification": "UNCLASSIFIED"
        },
        files={"file": ("life.txt", io.BytesIO(b"DOCUMENT CONTENT"), "text/plain")}
    )
    doc_id = upload_res.json()["id"]

    # Archive
    arch_res = client.post(f"/api/v1/documents/{doc_id}/archive", headers=headers_sp, json={
        "reason": "Case trial completed, court record sealed",
        "retention_years": 10
    })
    assert arch_res.status_code == 200
    assert arch_res.json()["status"] == "ARCHIVED"

    # Unarchive
    unarch_res = client.post(f"/api/v1/documents/{doc_id}/unarchive", headers=headers_sp)
    assert unarch_res.status_code == 200
    assert unarch_res.json()["status"] != "ARCHIVED"

    # Soft Delete (Move to Trash)
    del_res = client.delete(f"/api/v1/documents/{doc_id}", headers=headers_sp)
    assert del_res.status_code == 200

    # List Trash
    trash_res = client.get("/api/v1/documents/trash/list", headers=headers_sp)
    assert trash_res.status_code == 200
    assert any(d["id"] == doc_id for d in trash_res.json())

    # Restore from Trash
    rest_res = client.post(f"/api/v1/documents/{doc_id}/restore-deleted", headers=headers_sp)
    assert rest_res.status_code == 200
