"""Pytest test configuration and fixtures."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.core.constants import ClassificationLevel
from app.core.security import get_password_hash, create_access_token
from app.main import app
from app.models.organization import Organization
from app.models.department import Department
from app.models.position import Position
from app.models.user import User

from sqlalchemy.pool import StaticPool

# In-memory SQLite database for test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def setup_test_hierarchy(db_session):
    """Sets up Police Department with Superintendent, Investigator, and Clerk."""
    org = Organization(name="State Police Department", slug="state-police", jurisdiction="State")
    db_session.add(org)
    db_session.flush()

    dept = Department(name="Criminal Investigation", code="CID", organization_id=org.id)
    db_session.add(dept)
    db_session.flush()

    # Position 1: SP (Top Secret, can sign, can approve)
    pos_sp = Position(
        title="Superintendent of Police",
        code="SP",
        max_clearance=ClassificationLevel.TOP_SECRET.value,
        can_sign=True,
        can_approve=True,
        can_export=True,
        allowed_actions=["READ", "WRITE", "UPDATE", "APPROVE", "SIGN", "DELETE"],
        department_id=dept.id
    )
    # Position 2: Inspector (Confidential, can write, cannot sign)
    pos_insp = Position(
        title="Investigating Officer",
        code="IO",
        max_clearance=ClassificationLevel.CONFIDENTIAL.value,
        can_sign=False,
        can_approve=False,
        can_export=False,
        allowed_actions=["READ", "WRITE", "UPDATE"],
        department_id=dept.id
    )
    # Position 3: Clerk (Restricted, read-only)
    pos_clerk = Position(
        title="Police Clerk",
        code="CLK",
        max_clearance=ClassificationLevel.RESTRICTED.value,
        can_sign=False,
        can_approve=False,
        can_export=False,
        allowed_actions=["READ"],
        department_id=dept.id
    )
    db_session.add_all([pos_sp, pos_insp, pos_clerk])
    db_session.flush()

    # Users
    u_sp = User(
        email="sp@police.gov.in",
        full_name="SP Vikram Sharma",
        hashed_password=get_password_hash("Password123!"),
        badge_number="POL-001",
        clearance_level=ClassificationLevel.TOP_SECRET.value,
        organization_id=org.id,
        department_id=dept.id,
        position_id=pos_sp.id
    )
    u_insp = User(
        email="insp@police.gov.in",
        full_name="Inspector Das",
        hashed_password=get_password_hash("Password123!"),
        badge_number="POL-104",
        clearance_level=ClassificationLevel.CONFIDENTIAL.value,
        organization_id=org.id,
        department_id=dept.id,
        position_id=pos_insp.id
    )
    u_clerk = User(
        email="clerk@police.gov.in",
        full_name="Clerk Verma",
        hashed_password=get_password_hash("Password123!"),
        badge_number="POL-500",
        clearance_level=ClassificationLevel.RESTRICTED.value,
        organization_id=org.id,
        department_id=dept.id,
        position_id=pos_clerk.id
    )
    db_session.add_all([u_sp, u_insp, u_clerk])
    db_session.commit()

    return {
        "org": org,
        "dept": dept,
        "sp": u_sp,
        "insp": u_insp,
        "clerk": u_clerk,
        "token_sp": create_access_token(u_sp.id),
        "token_insp": create_access_token(u_insp.id),
        "token_clerk": create_access_token(u_clerk.id),
    }
