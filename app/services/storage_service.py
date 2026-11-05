"""Vault Storage Service: Manages physical file storage on disk."""
import shutil
from pathlib import Path
from typing import BinaryIO
from fastapi import UploadFile
from app.core.config import settings
from app.services.crypto_service import CryptoService


class StorageService:
    @classmethod
    def save_upload_file(cls, upload_file: UploadFile, subfolder: str = "documents") -> tuple[str, str, int]:
        """
        Saves an uploaded file to the secure vault directory.
        Returns (relative_file_path, sha256_hash, file_size_in_bytes).
        """
        base_path = settings.get_storage_path() / subfolder
        base_path.mkdir(parents=True, exist_ok=True)

        # Calculate SHA-256 fingerprint from the stream
        sha256_hash = CryptoService.calculate_sha256_stream(upload_file.file)

        # Store using the SHA-256 content address to guarantee immutability
        filename = f"{sha256_hash}_{upload_file.filename}"
        destination_path = base_path / filename

        upload_file.file.seek(0)
        with destination_path.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        file_size = destination_path.stat().st_size
        return str(destination_path), sha256_hash, file_size

    @classmethod
    def save_bytes(cls, data: bytes, original_filename: str, subfolder: str = "documents") -> tuple[str, str, int]:
        """Saves raw bytes into vault storage. Returns (path, sha256_hash, size)."""
        base_path = settings.get_storage_path() / subfolder
        base_path.mkdir(parents=True, exist_ok=True)

        sha256_hash = CryptoService.calculate_sha256_bytes(data)
        filename = f"{sha256_hash}_{original_filename}"
        destination_path = base_path / filename

        with destination_path.open("wb") as f:
            f.write(data)

        return str(destination_path), sha256_hash, len(data)
