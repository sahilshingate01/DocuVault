"""Tests for DBMS Viva demonstration endpoints and services."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.dbms_service import DBMSService


@pytest.fixture
def client():
    return TestClient(app)


def test_dbms_overview(client):
    res = client.get("/api/v1/dbms/overview")
    assert res.status_code == 200
    data = res.json()
    assert "Relational RDBMS" in data["engine"]
    assert data["total_tables"] >= 10
    assert len(data["table_stats"]) >= 10


def test_dbms_multi_table_join(client):
    res = client.get("/api/v1/dbms/join?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert "records" in data
    assert isinstance(data["records"], list)
    if len(data["records"]) > 0:
        row = data["records"][0]
        assert "document_number" in row
        assert "workspace_code" in row
        assert "sha256_hash" in row


def test_dbms_constraint_rejection(client):
    """Extra credit verification: Database kernel rejects duplicate document_number."""
    res = client.post("/api/v1/dbms/test-constraint")
    assert res.status_code == 200
    data = res.json()
    assert data["rejected"] is True
    assert data["status"] == "EXTRA_CREDIT_DEMONSTRATED"
    assert "UNIQUE constraint failed" in data["database_error"]


def test_dbms_atomic_transaction_success(client):
    res = client.post("/api/v1/dbms/test-transaction?simulate_failure=false")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMMITTED_SUCCESSFULLY"
    assert "document_id" in data
    assert "audit_sequence" in data


def test_dbms_atomic_transaction_rollback(client):
    res = client.post("/api/v1/dbms/test-transaction?simulate_failure=true")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ROLLED_BACK_SAFELY"
    assert data["records_persisted"] is False


def test_dbms_explain_query_plan(client):
    res = client.get("/api/v1/dbms/explain-plan")
    assert res.status_code == 200
    data = res.json()
    assert "indexed_query" in data
    assert "unindexed_query" in data
    assert "why_rejected_indexes" in data
    assert "scaling_100x_plan" in data
