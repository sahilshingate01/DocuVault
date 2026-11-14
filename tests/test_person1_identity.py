"""Comprehensive Tests for Person 1: Identity & Organization Management."""
import pytest
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    revoke_token,
    validate_password_complexity,
)
from app.models.organization import Organization
from app.models.department import Department
from app.models.position import Position
from app.models.user import User


def test_password_complexity_validator():
    """Validates strict password rules."""
    valid, msg = validate_password_complexity("weak")
    assert not valid
    assert "at least 8" in msg

    valid, msg = validate_password_complexity("nouppercase123!")
    assert not valid
    assert "uppercase" in msg

    valid, msg = validate_password_complexity("NOLOWERCASE123!")
    assert not valid
    assert "lowercase" in msg

    valid, msg = validate_password_complexity("NoDigitsHere!!")
    assert not valid
    assert "digit" in msg

    valid, msg = validate_password_complexity("NoSpecialChars123")
    assert not valid
    assert "special character" in msg

    valid, msg = validate_password_complexity("StrongP@ssw0rd2026!")
    assert valid
    assert msg is None


def test_jwt_refresh_token_lifecycle():
    """Validates refresh token generation, decoding, rotation, and revocation."""
    subject = "user-12345"
    token = create_refresh_token(subject)
    payload = decode_refresh_token(token)
    assert payload is not None
    assert payload["sub"] == subject
    assert payload["type"] == "refresh"

    # Revocation test
    revoke_token(token)
    revoked_payload = decode_refresh_token(token)
    assert revoked_payload is None


def test_user_registration_and_login_flow(client, db_session):
    """Integration test for user registration, login, and profile inspection."""
    email = "officer.sharma@police.gov.in"
    reg_payload = {
        "email": email,
        "full_name": "Officer Sharma",
        "password": "SecurePassword123!",
        "badge_number": "POL-999"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "token" in reg_data
    assert "refresh_token" in reg_data
    assert reg_data["user"]["email"] == email
    assert reg_data["user"]["public_key_pem"] is not None

    # Duplicate registration check
    dup_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 400

    # Login check
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePassword123!"})
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "token" in login_data
    assert "refresh_token" in login_data

    # Profile check with Bearer token
    headers = {"Authorization": f"Bearer {login_data['token']}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # Refresh token check
    ref_res = client.post("/api/v1/auth/refresh", json={"refresh_token": login_data["refresh_token"]})
    assert ref_res.status_code == 200
    ref_data = ref_res.json()
    assert "access_token" in ref_data
    assert "refresh_token" in ref_data


def test_account_lockout_on_failed_attempts(client, db_session):
    """Verifies that 5 failed login attempts lock the account."""
    email = "lockout.target@police.gov.in"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Lockout Target",
        "password": "ValidPassword123!"
    })

    # 5 failed attempts
    for _ in range(5):
        res = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword123!"})
        assert res.status_code == 401

    # 6th attempt must trigger account lockout (403)
    lock_res = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword123!"})
    assert lock_res.status_code == 403
    assert "temporarily locked" in lock_res.json()["detail"]


def test_organization_and_department_management(client, setup_test_hierarchy):
    """Tests Organization and Department CRUD APIs."""
    headers = {"Authorization": f"Bearer {setup_test_hierarchy['token_sp']}"}
    org_id = setup_test_hierarchy["org"].id

    # List organizations
    orgs_res = client.get("/api/v1/organizations", headers=headers)
    assert orgs_res.status_code == 200
    assert len(orgs_res.json()) > 0

    # Get organization details
    org_detail_res = client.get(f"/api/v1/organizations/{org_id}", headers=headers)
    assert org_detail_res.status_code == 200
    assert "department_count" in org_detail_res.json()

    # Create department
    dept_res = client.post("/api/v1/departments", headers=headers, json={
        "name": "Special Cyber Forensics Cell",
        "code": "CYBER-CELL",
        "organization_id": org_id,
        "description": "High tech digital evidence unit"
    })
    assert dept_res.status_code == 201
    dept_id = dept_res.json()["id"]

    # List departments
    list_depts = client.get(f"/api/v1/departments?organization_id={org_id}", headers=headers)
    assert list_depts.status_code == 200
    assert any(d["code"] == "CYBER-CELL" for d in list_depts.json())

    # Create custom position (e.g. SP, Judge, CEO, Manager, Employee)
    pos_res = client.post("/api/v1/positions", headers=headers, json={
        "title": "Lead Forensics Specialist",
        "code": "LFS",
        "designation_type": "SP",
        "max_clearance": "SECRET",
        "can_sign": True,
        "can_approve": True,
        "allowed_actions": ["READ", "WRITE", "SIGN", "APPROVE"],
        "department_id": dept_id
    })
    assert pos_res.status_code == 201
    pos_data = pos_res.json()
    assert pos_data["designation_type"] == "SP"
    assert pos_data["can_sign"] is True
