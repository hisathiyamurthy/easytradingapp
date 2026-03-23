"""TOTP (Time-based One-Time Password) service for 2FA."""
import base64
import secrets
from typing import Optional
import pyotp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.auth_models import User
from core.security import get_password_hash


class TOTPService:
    """Service for TOTP-based two-factor authentication."""

    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()

    @staticmethod
    def get_totp(secret: str) -> pyotp.TOTP:
        """Get TOTP object for a secret."""
        return pyotp.TOTP(secret)

    @staticmethod
    def generate_qr_code(secret: str, email: str, issuer: str = "EasyTradingApp") -> str:
        """Generate QR code URL for authenticator apps."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)

    @staticmethod
    def verify_code(secret: str, code: str, window: int = 1) -> bool:
        """Verify a TOTP code with configurable window for clock drift."""
        if not secret or not code:
            return False
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)

    @staticmethod
    def generate_backup_codes(count: int = 8) -> list[str]:
        """Generate backup codes for account recovery."""
        return [secrets.token_hex(4).upper() for _ in range(count)]


class MFAService:
    """Service for managing user MFA settings."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.totp_service = TOTPService()

    async def setup_mfa(self, user_id: str) -> dict:
        """Initialize MFA setup for a user."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        if user.mfa_enabled:
            raise ValueError("MFA is already enabled")

        secret = self.totp_service.generate_secret()
        qr_url = self.totp_service.generate_qr_code(secret, user.email)

        user.mfa_secret = secret
        await self.db.commit()

        return {
            "secret": secret,
            "qr_code_url": qr_url,
            "message": "Scan the QR code with your authenticator app, then verify with a code"
        }

    async def enable_mfa(self, user_id: str, code: str) -> bool:
        """Enable MFA after verifying the first code."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")

        if not user.mfa_secret:
            raise ValueError("MFA setup not initiated. Call /setup first.")

        if not self.totp_service.verify_code(user.mfa_secret, code):
            raise ValueError("Invalid verification code")

        user.mfa_enabled = True
        user.mfa_secret = user.mfa_secret
        await self.db.commit()

        return True

    async def disable_mfa(self, user_id: str, code: str, password: str) -> bool:
        """Disable MFA with verification code and password."""
        from core.security import verify_password

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")

        if not user.mfa_enabled:
            return True

        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid password")

        if not self.totp_service.verify_code(user.mfa_secret, code):
            raise ValueError("Invalid verification code")

        user.mfa_enabled = False
        user.mfa_secret = None
        await self.db.commit()

        return True

    async def get_mfa_status(self, user_id: str) -> dict:
        """Get MFA status for a user."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")

        return {
            "mfa_enabled": user.mfa_enabled,
            "mfa_type": "totp" if user.mfa_enabled else None
        }


async def verify_mfa_code(user_id: str, code: str, db: AsyncSession) -> bool:
    """Verify MFA code for a user during login."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.mfa_enabled or not user.mfa_secret:
        return False

    totp_service = TOTPService()
    return totp_service.verify_code(user.mfa_secret, code)
