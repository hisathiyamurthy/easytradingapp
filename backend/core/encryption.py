from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from typing import Optional

from core.config import get_settings

settings = get_settings()


class EncryptionService:
    """AES-256-GCM encryption for sensitive data like API keys."""
    
    def __init__(self, key: Optional[str] = None, salt: Optional[str] = None):
        self.key = key or settings.ENCRYPTION_KEY
        self.salt = salt or settings.ENCRYPTION_SALT
        if not self.key or not self.salt:
            raise ValueError("ENCRYPTION_KEY and ENCRYPTION_SALT must be set in environment")
        self._fernet = self._derive_key(self.key, self.salt)
    
    def _derive_key(self, password: str, salt_str: str) -> Fernet:
        """Derive a Fernet key from password using PBKDF2."""
        salt = salt_str.encode() if isinstance(salt_str, str) else salt_str
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt plaintext string."""
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")
        return self._fernet.encrypt(plaintext.encode())
    
    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt ciphertext to string."""
        if not ciphertext:
            raise ValueError("Cannot decrypt empty bytes")
        return self._fernet.decrypt(ciphertext).decode()
    
    def encrypt_dict(self, data: dict) -> dict:
        """Encrypt all string values in a dictionary."""
        return {k: self.encrypt(str(v)) if isinstance(v, str) else v for k, v in data.items()}
    
    def decrypt_dict(self, data: dict) -> dict:
        """Decrypt all bytes values in a dictionary back to strings."""
        result = {}
        for k, v in data.items():
            if isinstance(v, bytes):
                try:
                    result[k] = self.decrypt(v)
                except Exception:
                    result[k] = v
            else:
                result[k] = v
        return result


def get_encryption_service() -> EncryptionService:
    """Get encryption service instance."""
    return EncryptionService()
