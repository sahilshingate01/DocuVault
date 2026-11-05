"""System-wide enums and domain constants."""
from enum import Enum


class ClassificationLevel(str, Enum):
    UNCLASSIFIED = "UNCLASSIFIED"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"
    SECRET = "SECRET"
    TOP_SECRET = "TOP_SECRET"

    @classmethod
    def get_rank(cls, level: "ClassificationLevel | str") -> int:
        ranks = {
            cls.UNCLASSIFIED.value: 1,
            cls.RESTRICTED.value: 2,
            cls.CONFIDENTIAL.value: 3,
            cls.SECRET.value: 4,
            cls.TOP_SECRET.value: 5,
        }
        val = level.value if isinstance(level, cls) else str(level)
        return ranks.get(val, 0)

    @classmethod
    def can_access(cls, user_clearance: "ClassificationLevel | str", doc_level: "ClassificationLevel | str") -> bool:
        """Clearance must be equal or higher in rank than document classification."""
        return cls.get_rank(user_clearance) >= cls.get_rank(doc_level)


class ActionType(str, Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    READ = "READ"
    WRITE = "WRITE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    DOWNLOAD = "DOWNLOAD"
    APPROVE = "APPROVE"
    SIGN = "SIGN"
    VERIFY_SIGNATURE = "VERIFY_SIGNATURE"
    VERIFY_INTEGRITY = "VERIFY_INTEGRITY"
    ACCESS_DENIED = "ACCESS_DENIED"
    TAMPER_DETECTED = "TAMPER_DETECTED"


class DocumentStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    SIGNED = "SIGNED"
    ARCHIVED = "ARCHIVED"


class ResourceType(str, Enum):
    ORGANIZATION = "ORGANIZATION"
    DEPARTMENT = "DEPARTMENT"
    POSITION = "POSITION"
    USER = "USER"
    WORKSPACE = "WORKSPACE"
    DOCUMENT = "DOCUMENT"
    DOCUMENT_VERSION = "DOCUMENT_VERSION"
    SIGNATURE = "SIGNATURE"
    AUDIT_LOG = "AUDIT_LOG"
