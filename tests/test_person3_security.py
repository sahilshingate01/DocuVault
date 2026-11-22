"""Comprehensive Tests for Person 3: Authorization, Security & Audit Management."""
import io
import pytest
from app.models.document import Document
from app.models.temporary_clearance import TemporaryClearance


def test_abac_evaluation_engine_rules(client, setup_test_hierarchy):
    """Tests ABAC policy engine directly, validating allow/deny and rule traces."""
    headers_sp = {"Authorization": f"Bearer {setup_test_hierarchy['token_sp']}"}
    headers_clerk = {"Authorization": f"Bearer {setup_test_hierarchy['token_clerk']}"}

    # Create classified workspace (Top Secret)
    ws_res = client.post("/api/v1/workspaces", headers=headers_sp, json={
        "name": "Classified Intelligence Room",
        "code": "WS-INTEL-01",
        "classification": "TOP_SECRET"
    })
    ws_id = ws_res.json()["id"]

    # 1. SP (Top Secret) should be ALLOWED
    sp_eval = client.post("/api/v1/security/evaluate", headers=headers_sp, json={
        "action": "READ",
        "resource_type": "WORKSPACE",
        "resource_id": ws_id
    })
    assert sp_eval.status_code == 200
    assert sp_eval.json()["decision"] == "ALLOW"
    assert sp_eval.json()["allowed"] is True

    # 2. Clerk (Restricted clearance) should be DENIED with CLEARANCE_INSUFFICIENT
    clerk_eval = client.post("/api/v1/security/evaluate", headers=headers_clerk, json={
        "action": "READ",
        "resource_type": "WORKSPACE",
        "resource_id": ws_id
    })
    assert clerk_eval.status_code == 200
    assert clerk_eval.json()["decision"] == "DENY"
    assert clerk_eval.json()["allowed"] is False
    assert clerk_eval.json()["code"] == "CLEARANCE_INSUFFICIENT"


def test_temporary_clearance_delegation_flow(client, setup_test_hierarchy):
    """Tests granting time-bound elevated clearance to allow access to classified document."""
    headers_sp = {"Authorization": f"Bearer {setup_test_hierarchy['token_sp']}"}
    headers_clerk = {"Authorization": f"Bearer {setup_test_hierarchy['token_clerk']}"}
    clerk_id = setup_test_hierarchy["clerk"].id

    # Create workspace & secret document
    ws_res = client.post("/api/v1/workspaces", headers=headers_sp, json={
        "name": "State vs. Defense Case",
        "code": "WS-SVD-01",
        "classification": "SECRET"
    })
    ws_id = ws_res.json()["id"]

    doc_res = client.post(
        "/api/v1/documents/upload",
        headers=headers_sp,
        data={
            "title": "Confidential Witness Deposition",
            "document_number": "DOC-DEP-001",
            "workspace_id": ws_id,
            "classification": "SECRET"
        },
        files={"file": ("dep.txt", io.BytesIO(b"SECRET TESTIMONY"), "text/plain")}
    )
    doc_id = doc_res.json()["id"]

    # Clerk initially rejected with 403
    pre_res = client.get(f"/api/v1/documents/{doc_id}", headers=headers_clerk)
    assert pre_res.status_code == 403

    # SP grants 48-hour temporary clearance to Clerk for this document
    grant_res = client.post("/api/v1/clearance/grant", headers=headers_sp, json={
        "user_id": clerk_id,
        "granted_clearance": "SECRET",
        "document_id": doc_id,
        "reason": "Authorized court document processing",
        "valid_hours": 48
    })
    assert grant_res.status_code == 201
    grant_id = grant_res.json()["id"]

    # Clerk now authorized and succeeds (200)
    post_res = client.get(f"/api/v1/documents/{doc_id}", headers=headers_clerk)
    assert post_res.status_code == 200
    assert post_res.json()["id"] == doc_id

    # Revoke clearance early
    rev_res = client.post(f"/api/v1/clearance/{grant_id}/revoke?reason=Task+completed", headers=headers_sp)
    assert rev_res.status_code == 200
    assert rev_res.json()["is_revoked"] is True

    # Clerk access immediately severed (403)
    after_rev = client.get(f"/api/v1/documents/{doc_id}", headers=headers_clerk)
    assert after_rev.status_code == 403


def test_document_audit_trail_and_export(client, setup_test_hierarchy):
    """Tests document-specific audit trail and forensic CSV export."""
    headers_sp = {"Authorization": f"Bearer {setup_test_hierarchy['token_sp']}"}

    ws_res = client.post("/api/v1/workspaces", headers=headers_sp, json={
        "name": "Audit Workspace",
        "code": "WS-AUD-01",
        "classification": "UNCLASSIFIED"
    })
    ws_id = ws_res.json()["id"]

    doc_res = client.post(
        "/api/v1/documents/upload",
        headers=headers_sp,
        data={
            "title": "Audited Document",
            "document_number": "DOC-AUD-001",
            "workspace_id": ws_id,
            "classification": "UNCLASSIFIED"
        },
        files={"file": ("audit.txt", io.BytesIO(b"AUDIT DATA"), "text/plain")}
    )
    doc_id = doc_res.json()["id"]

    # Fetch document audit trail
    trail_res = client.get(f"/api/v1/audit/documents/{doc_id}", headers=headers_sp)
    assert trail_res.status_code == 200
    trail = trail_res.json()
    assert len(trail) > 0

    # Export audit ledger as CSV
    export_res = client.get("/api/v1/audit/export?export_format=csv", headers=headers_sp)
    assert export_res.status_code == 200
    assert "Sequence" in export_res.text
    assert "EntryHash" in export_res.text


def test_security_dashboard_and_alerts(client, setup_test_hierarchy):
    """Tests security dashboard metrics and alert aggregation."""
    headers_sp = {"Authorization": f"Bearer {setup_test_hierarchy['token_sp']}"}

    # Query security dashboard
    dash_res = client.get("/api/v1/security/dashboard", headers=headers_sp)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "ledger_integrity" in dash_data
    assert "activity_metrics_24h" in dash_data
    assert dash_data["ledger_integrity"]["is_valid"] is True

    # Query security alerts
    alert_res = client.get("/api/v1/security/alerts", headers=headers_sp)
    assert alert_res.status_code == 200
    assert "active_alerts_count" in alert_res.json()

