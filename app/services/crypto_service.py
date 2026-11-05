"""Cryptographic Service: SHA-256 fingerprinting, asymmetric keypairs, and digital signatures."""
import hashlib
from typing import BinaryIO, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature


class CryptoService:
    CHUNK_SIZE = 64 * 1024  # 64 KB streaming chunks

    @classmethod
    def calculate_sha256_stream(cls, stream: BinaryIO) -> str:
        """Calculates SHA-256 hexadecimal digest by streaming file chunks."""
        hasher = hashlib.sha256()
        stream.seek(0)
        while chunk := stream.read(cls.CHUNK_SIZE):
            hasher.update(chunk)
        stream.seek(0)
        return hasher.hexdigest()

    @classmethod
    def calculate_sha256_bytes(cls, data: bytes) -> str:
        """Calculates SHA-256 hexadecimal digest for raw in-memory bytes."""
        return hashlib.sha256(data).hexdigest()

    @classmethod
    def generate_keypair(cls, key_size: int = 2048) -> Tuple[str, str]:
        """Generates an RSA Private/Public Keypair in PEM format."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode("utf-8")

        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        return private_pem, public_pem

    @classmethod
    def sign_digest(cls, private_key_pem: str, sha256_digest: str) -> str:
        """Digitally signs a SHA-256 digest using RSA-PSS padding."""
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None
        )
        signature = private_key.sign(
            sha256_digest.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature.hex()

    @classmethod
    def verify_signature(cls, public_key_pem: str, sha256_digest: str, signature_hex: str) -> bool:
        """Verifies if an RSA-PSS digital signature matches the given SHA-256 digest."""
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode("utf-8")
            )
            public_key.verify(
                bytes.fromhex(signature_hex),
                sha256_digest.encode("utf-8"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except (InvalidSignature, ValueError, Exception):
            return False
