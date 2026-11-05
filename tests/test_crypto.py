"""Tests for SHA-256 fingerprinting and digital signature verification."""
import io
from app.services.crypto_service import CryptoService


def test_sha256_stream_calculation():
    data = b"State of Police vs. Malgudi: Confidential Witness Statement"
    stream = io.BytesIO(data)
    digest = CryptoService.calculate_sha256_stream(stream)
    assert len(digest) == 64
    assert digest == CryptoService.calculate_sha256_bytes(data)


def test_digital_signature_generation_and_verification():
    priv_pem, pub_pem = CryptoService.generate_keypair()
    sha256_fingerprint = CryptoService.calculate_sha256_bytes(b"Ballistics Report #402")

    # Sign digest
    sig_hex = CryptoService.sign_digest(priv_pem, sha256_fingerprint)
    assert len(sig_hex) > 0

    # Verify signature against public key
    is_valid = CryptoService.verify_signature(pub_pem, sha256_fingerprint, sig_hex)
    assert is_valid is True

    # Tampered digest must fail verification
    tampered_digest = CryptoService.calculate_sha256_bytes(b"Tampered Ballistics Report")
    is_invalid = CryptoService.verify_signature(pub_pem, tampered_digest, sig_hex)
    assert is_invalid is False


def test_invalid_key_signature_rejection():
    _, pub_pem1 = CryptoService.generate_keypair()
    priv_pem2, _ = CryptoService.generate_keypair()

    digest = CryptoService.calculate_sha256_bytes(b"Executive Directive")
    sig_hex = CryptoService.sign_digest(priv_pem2, digest)

    # Verifying with mismatched public key must fail
    assert CryptoService.verify_signature(pub_pem1, digest, sig_hex) is False
