"""Diff Service: Mathematical comparison and statement modification inspector."""
import os
import difflib
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.user import User
from app.core.constants import ActionType
from app.services.access_control import AccessControlService
from app.services.audit_service import AuditService


class DiffService:
    @classmethod
    def compare_versions(
        cls,
        db: Session,
        document_id: str,
        v1_num: int,
        v2_num: int,
        user: User
    ) -> Dict[str, Any]:
        """
        Calculates cryptographic and line-by-line diff between two document versions.
        Detects tampering or altered witness statements / contract modifications.
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        AccessControlService.authorize_document(db, user, doc, ActionType.READ.value)

        ver1 = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == doc.id,
            DocumentVersion.version_number == v1_num
        ).first()

        ver2 = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == doc.id,
            DocumentVersion.version_number == v2_num
        ).first()

        if not ver1 or not ver2:
            raise HTTPException(status_code=404, detail="One or both document versions not found.")

        # Read text content from files if readable, else binary note
        text_v1 = cls._read_file_text(ver1.file_path)
        text_v2 = cls._read_file_text(ver2.file_path)

        lines_v1 = text_v1.splitlines()
        lines_v2 = text_v2.splitlines()

        matcher = difflib.SequenceMatcher(None, lines_v1, lines_v2)
        similarity = round(matcher.ratio(), 4)

        unified = list(difflib.unified_diff(
            lines_v1,
            lines_v2,
            fromfile=f"v{v1_num}_{ver1.original_filename}",
            tofile=f"v{v2_num}_{ver2.original_filename}",
            lineterm=""
        ))

        line_by_line: List[Dict[str, Any]] = []
        lines_added = 0
        lines_deleted = 0
        lines_modified = 0

        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == "equal":
                for idx, line in enumerate(lines_v1[i1:i2]):
                    line_by_line.append({
                        "line_number_v1": i1 + idx + 1,
                        "line_number_v2": j1 + idx + 1,
                        "operation": "EQUAL",
                        "content": line
                    })
            elif op == "delete":
                for idx, line in enumerate(lines_v1[i1:i2]):
                    lines_deleted += 1
                    line_by_line.append({
                        "line_number_v1": i1 + idx + 1,
                        "line_number_v2": None,
                        "operation": "DELETE",
                        "content": line
                    })
            elif op == "insert":
                for idx, line in enumerate(lines_v2[j1:j2]):
                    lines_added += 1
                    line_by_line.append({
                        "line_number_v1": None,
                        "line_number_v2": j1 + idx + 1,
                        "operation": "ADD",
                        "content": line
                    })
            elif op == "replace":
                lines_modified += max(i2 - i1, j2 - j1)
                for line in lines_v1[i1:i2]:
                    line_by_line.append({
                        "line_number_v1": i1 + 1,
                        "line_number_v2": None,
                        "operation": "DELETE",
                        "content": line
                    })
                for line in lines_v2[j1:j2]:
                    line_by_line.append({
                        "line_number_v1": None,
                        "line_number_v2": j1 + 1,
                        "operation": "ADD",
                        "content": line
                    })

        # Forensic tampering assessment
        if ver1.sha256_hash == ver2.sha256_hash:
            assessment = "IDENTICAL: Both versions have byte-identical SHA-256 fingerprints."
        elif similarity > 0.85:
            assessment = f"MINOR ALTERATION: {round((1 - similarity) * 100, 1)}% variance detected. Potential statement editing or clause amendment."
        elif similarity > 0.40:
            assessment = f"MAJOR REVISION: Substantial statement or contract rewrite. Critical inspection advised."
        else:
            assessment = "ENTIRELY REPLACED: Content similarity below 40%. Full file divergence."

        AuditService.record(
            db=db,
            action="VERSION_DIFF_INSPECTED",
            resource_type="DOCUMENT_VERSION",
            resource_id=doc.id,
            actor=user,
            details={
                "doc_title": doc.title,
                "v1": v1_num,
                "v2": v2_num,
                "similarity": similarity,
                "tampering_assessment": assessment
            }
        )

        return {
            "document_id": doc.id,
            "document_title": doc.title,
            "version_1": v1_num,
            "version_2": v2_num,
            "v1_sha256": ver1.sha256_hash,
            "v2_sha256": ver2.sha256_hash,
            "similarity_ratio": similarity,
            "total_lines_v1": len(lines_v1),
            "total_lines_v2": len(lines_v2),
            "lines_added": lines_added,
            "lines_deleted": lines_deleted,
            "lines_modified": lines_modified,
            "unified_diff": "\n".join(unified),
            "line_by_line": line_by_line,
            "tampering_assessment": assessment
        }

    @staticmethod
    def _read_file_text(path: str) -> str:
        if not os.path.exists(path):
            return "[File missing from vault storage]"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return "[Binary content - text diff unavailable]"
