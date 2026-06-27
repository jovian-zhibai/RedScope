"""Credential encryption: encrypts/decrypts sensitive data at rest using Fernet."""

from cryptography.fernet import Fernet
from backend.config import get_settings
import hashlib
import base64


def _get_fernet() -> Fernet:
    settings = get_settings()
    import hashlib as hl
    # Derive salt from SECRET_KEY so each deployment has unique salt
    salt = hl.sha256(settings.secret_key.encode()).digest()[:16]
    key = hl.pbkdf2_hmac("sha256", settings.secret_key.encode(), salt, iterations=100_000)
    key_b64 = base64.urlsafe_b64encode(key)
    return Fernet(key_b64)


def encrypt_value(plaintext: str) -> str:
    if not plaintext:
        return ""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        f = _get_fernet()
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        return "[解密失败]"


def mask_value(value: str, show_chars: int = 4) -> str:
    if not value or len(value) <= show_chars:
        return "****"
    return value[:show_chars] + "****"
