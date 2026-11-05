"""Tests for Security Clearance, RBAC, and Position Capability Enforcement."""
import pytest
from app.core.constants import ClassificationLevel, ActionType
from app.services.access_control import AccessControlService, SecurityViolationException
from app.models.workspace import Workspace
from app.models.document import Document


def test_clearance_matrix():
    # TOP_SECRET can access all levels
    assert ClassificationLevel.can_access("TOP_SECRET", "TOP_SECRET") is True
    assert ClassificationLevel.can_access("TOP_SECRET", "SECRET") is True
    assert ClassificationLevel.can_access("TOP_SECRET", "UNCLASSIFIED") is True

    # CONFIDENTIAL cannot access SECRET or TOP_SECRET
    assert ClassificationLevel.can_access("CONFIDENTIAL", "CONFIDENTIAL") is True
    assert ClassificationLevel.can_access("CONFIDENTIAL", "SECRET") is False
    assert ClassificationLevel.can_access("CONFIDENTIAL", "TOP_SECRET") is False


def test_document_clearance_access_control(db_session, setup_test_hierarchy):
    sp = setup_test_hierarchy["sp"]
    clerk = setup_test_hierarchy["clerk"]
    org = setup_test_hierarchy["org"]

    workspace = Workspace(
        name="Case 402",
        code="CASE-402",
        classification=ClassificationLevel.RESTRICTED.value,
        organization_id=org.id
    )
    db_session.add(workspace)
    db_session.flush()

    top_secret_doc = Document(
        title="Classified Informant Identity",
        document_number="DOC-TS-001",
        classification=ClassificationLevel.TOP_SECRET.value,
        workspace_id=workspace.id,
        created_by_id=sp.id
    )
    db_session.add(top_secret_doc)
    db_session.commit()

    # SP with TOP_SECRET clearance may READ
    assert AccessControlService.authorize_document(db_session, sp, top_secret_doc, ActionType.READ.value) is True

    # Clerk with RESTRICTED clearance must be REJECTED with SecurityViolationException
    with pytest.raises(SecurityViolationException):
        AccessControlService.authorize_document(db_session, clerk, top_secret_doc, ActionType.READ.value)


def test_position_action_authority(db_session, setup_test_hierarchy):
    sp = setup_test_hierarchy["sp"]
    insp = setup_test_hierarchy["insp"]

    # SP has can_sign=True
    assert AccessControlService.can_perform_action(sp, ActionType.SIGN.value) is True

    # Inspector has can_sign=False
    assert AccessControlService.can_perform_action(insp, ActionType.SIGN.value) is False
