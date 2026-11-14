
"""Vault storage service for safely storing uploaded document versions."""

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException, UploadFile

from app.core.config import settings


class StorageService:
    """Stores document bytes and returns their SHA-256 fingerprint and size."""

    CHUNK_SIZE = 64 * 1024
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MiB

    @staticmethod
    def _safe_filename(original_filename: str | None) -> str:
        """Keep only a safe basename; never trust a client-supplied path."""
        supplied_name = (original_filename or "document.bin").replace("\\", "/")
        basename = Path(supplied_name).name
        safe_name = re.sub(r"[^A-Za-z0-9._ -]", "_", basename).strip(" .")
        return safe_name or "document.bin"

    @classmethod
    def save_upload_file(
        cls,
        upload_file: UploadFile,
        subfolder: str = "documents",
    ) -> tuple[str, str, int]:
        """Stream an upload to disk, enforcing a size limit and hashing its bytes.

        Returns (absolute_file_path, sha256_hex_digest, file_size_bytes).
        A temporary file is atomically moved into place after the complete upload
        has been read, so an interrupted upload is not exposed as a stored file.
        """
        base_path = settings.get_storage_path() / subfolder
        base_path.mkdir(parents=True, exist_ok=True)
        safe_filename = cls._safe_filename(upload_file.filename)

        upload_file.file.seek(0)
        hasher = hashlib.sha256()
        file_size = 0
        temp_path: str | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=base_path, prefix=".upload-", delete=False
            ) as temp_file:
                temp_path = temp_file.name

                while chunk := upload_file.file.read(cls.CHUNK_SIZE):
                    file_size += len(chunk)

                    if file_size > cls.MAX_UPLOAD_SIZE:
                        raise HTTPException(
                            status_code=413,
                            detail=(
                                f"File is too large. Maximum upload size is "
                                f"{cls.MAX_UPLOAD_SIZE // (1024 * 1024)} MB."
                            ),
                        )

                    hasher.update(chunk)
                    temp_file.write(chunk)

            sha256_hash = hasher.hexdigest()
            destination_path = base_path / f"{sha256_hash}_{safe_filename}"

            # Reuse an existing file only if its contents are still intact.
            if destination_path.exists():
                existing_hasher = hashlib.sha256()

                with open(destination_path, "rb") as existing_file:
                    while chunk := existing_file.read(cls.CHUNK_SIZE):
                        existing_hasher.update(chunk)

                if existing_hasher.hexdigest() == sha256_hash:
                    os.remove(temp_path)
                else:
                    os.replace(temp_path, destination_path)
            else:
                os.replace(temp_path, destination_path)

            temp_path = None

            return str(destination_path), sha256_hash, file_size

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

            upload_file.file.seek(0)

    @classmethod
    def save_bytes(
        cls,
        data: bytes,
        original_filename: str,
        subfolder: str = "documents",
    ) -> tuple[str, str, int]:
        """Save raw bytes using the same content-addressed naming convention."""
        if len(data) > cls.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"File is too large. Maximum upload size is "
                    f"{cls.MAX_UPLOAD_SIZE // (1024 * 1024)} MB."
                ),
            )

        base_path = settings.get_storage_path() / subfolder
        base_path.mkdir(parents=True, exist_ok=True)

        sha256_hash = hashlib.sha256(data).hexdigest()
        safe_filename = cls._safe_filename(original_filename)
        destination_path = base_path / f"{sha256_hash}_{safe_filename}"

        if not destination_path.exists():
            destination_path.write_bytes(data)
        else:
            # Do not silently reuse a corrupted existing file.
            existing_hash = hashlib.sha256(destination_path.read_bytes()).hexdigest()

            if existing_hash != sha256_hash:
                destination_path.write_bytes(data)

        return str(destination_path), sha256_hash, len(data)
