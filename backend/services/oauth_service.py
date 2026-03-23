"""OAuth2/Google authentication service."""
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from jose import jwt, JWTError

from core.config import get_settings
from core.security import get_password_hash
from models.auth_models import User, UserSession, VerificationToken
from schemas.auth_schemas import LoginResponse, UserResponse
from schemas.enums import UserRole

settings = get_settings()


class OAuth2Service:
    """Service for OAuth2 authentication (Google, etc.)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_google(self, google_token: str) -> LoginResponse:
        """Authenticate user using Google OAuth2 token."""
        google_user = await self._verify_google_token(google_token)
        
        if not google_user:
            raise ValueError("Invalid Google token")

        email = google_user.get("email")
        if not email:
            raise ValueError("Invalid Google token: no email")
        user = await self._find_or_create_user(email, google_user, "google")

        return await self._create_login_response(user)

    async def _verify_google_token(self, token: str) -> Optional[dict]:
        """Verify Google OAuth2 token and return user info."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        return None

    async def _find_or_create_user(self, email: str, oauth_data: dict, provider: str = "google") -> User:
        """Find existing user or create new one from OAuth data."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email=email.lower(),
                password_hash=get_password_hash(secrets.token_urlsafe(32)),
                first_name=oauth_data.get("given_name", ""),
                last_name=oauth_data.get("family_name", ""),
                is_verified=True,
                role=UserRole.TRADER,
                oauth_provider=provider,
                oauth_provider_id=oauth_data.get("sub"),
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        else:
            user.oauth_provider = provider
            user.oauth_provider_id = oauth_data.get("sub")
            await self.db.commit()

        return user

    async def _create_login_response(self, user: User) -> LoginResponse:
        """Create login response with tokens."""
        from core.security import create_access_token, create_refresh_token

        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()

        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)}
        )

        session = UserSession(
            user_id=user.id,
            token_hash=hashlib.sha256(access_token.encode()).hexdigest(),
            refresh_token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        self.db.add(session)
        await self.db.commit()

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=user.phone,
                is_active=user.is_active,
                is_verified=user.is_verified,
                mfa_enabled=user.mfa_enabled,
                failed_login_attempts=user.failed_login_attempts,
                locked_until=user.locked_until,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )


class OAuth2GoogleCallback:
    """Handler for Google OAuth2 callback."""

    @staticmethod
    async def get_authorization_url(client_id: str, redirect_uri: str, state: str) -> str:
        """Generate Google OAuth2 authorization URL."""
        import urllib.parse
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    @staticmethod
    async def exchange_code_for_token(
        client_id: str, client_secret: str, code: str, redirect_uri: str
    ) -> dict:
        """Exchange authorization code for access token."""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
            raise ValueError(f"Token exchange failed: {response.text}")
