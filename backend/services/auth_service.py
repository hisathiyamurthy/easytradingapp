"""Authentication service."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
import hashlib
import secrets

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from jose import jwt, JWTError
from fastapi import HTTPException, status, Request

from core.config import get_settings
from core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    TokenData,
    UserRole,
    get_token_blacklist,
)
from models.auth_models import User, UserSession, PasswordResetToken, VerificationToken, RegistrationRequest
from schemas.auth_schemas import UserCreate, LoginResponse, UserResponse, UserRegistration, UserStatus
from schemas.enums import UserStatus as EnumUserStatus

settings = get_settings()


class AuthService:
    """Authentication service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, user_data: UserRegistration, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> User:
        """Register a new user with admin approval required."""
        email = user_data.email.lower()
        
        # Check if email exists
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Check for recent registration requests from same IP (spam prevention)
        result = await self.db.execute(
            select(RegistrationRequest).where(
                and_(
                    RegistrationRequest.ip_address == ip_address,
                    RegistrationRequest.created_at > datetime.now(timezone.utc) - timedelta(hours=1)
                )
            )
        )
        recent_requests = result.scalars().all()
        
        if len(recent_requests) >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many registration attempts. Please try again later."
            )

        # Check for recent registration requests from same email
        result = await self.db.execute(
            select(RegistrationRequest).where(
                and_(
                    RegistrationRequest.email == email,
                    RegistrationRequest.created_at > datetime.now(timezone.utc) - timedelta(hours=1)
                )
            )
        )
        email_recent = result.scalars().all()
        
        if len(email_recent) >= 2:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many registration attempts for this email. Please try again later."
            )

        # Create new user with PENDING status
        user = User(
            email=email,
            password_hash=get_password_hash(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            role=UserRole.TRADER,
            status=EnumUserStatus.PENDING,  # Default to pending
        )
        
        self.db.add(user)
        
        # Create registration request record
        reg_request = RegistrationRequest(
            email=email,
            ip_address=ip_address or "unknown",
            user_agent=user_agent,
            request_count=len(recent_requests) + 1,
            last_request_at=datetime.now(timezone.utc),
        )
        self.db.add(reg_request)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user

    async def authenticate_user(
        self, email: str, password: str, ip_address: Optional[str] = None
    ) -> LoginResponse:
        """Authenticate user and return tokens."""
        # Find user
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()

        # Check if user exists and password is correct
        if not user or not verify_password(password, user.password_hash):
            # Increment failed attempts
            if user:
                user.failed_login_attempts += 1
                
                # Lock account after 5 failed attempts
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                
                await self.db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Check if account is locked
        if user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked. Please try again later."
            )

        # Check account status before allowing login
        blocked_reason = user.login_blocked_reason
        if blocked_reason:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=blocked_reason
            )

        # Check if account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled. Contact support."
            )

        # Reset failed attempts and update last login
        user.failed_login_attempts = 0
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()

        # Generate tokens
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)}
        )

        # Create session
        session = UserSession(
            user_id=user.id,
            token_hash=hashlib.sha256(access_token.encode()).hexdigest(),
            refresh_token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(user)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                status=user.status,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=user.phone,
                is_active=user.is_active,
                is_verified=user.is_verified,
                mfa_enabled=user.mfa_enabled,
                failed_login_attempts=user.failed_login_attempts,
                locked_until=user.locked_until,
                last_login_at=user.last_login_at,
                approved_by=user.approved_by,
                approved_at=user.approved_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )

    async def logout(self, user_id: UUID, token: str) -> bool:
        """Logout user by invalidating session and blacklisting token."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        result = await self.db.execute(
            select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.token_hash == token_hash,
                )
            )
        )
        session = result.scalar_one_or_none()
        
        if session:
            session.is_active = False
            await self.db.commit()
        
        blacklist = get_token_blacklist()
        from jose import jwt as jose_jwt
        try:
            payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            exp = payload.get("exp", 0)
            ttl = max(exp - int(datetime.now(timezone.utc).timestamp()), 60)
            blacklist.add_to_blacklist(token, ttl)
        except Exception:
            blacklist.add_to_blacklist(token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        
        return True

    async def logout_all_sessions(self, user_id: UUID) -> int:
        """Logout all user sessions."""
        result = await self.db.execute(
            select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                )
            )
        )
        sessions = result.scalars().all()
        
        count = 0
        for session in sessions:
            session.is_active = False
            count += 1
        
        await self.db.commit()
        return count

    async def refresh_access_token(self, refresh_token: str) -> LoginResponse:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(
                refresh_token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

        # Find user
        result = await self.db.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Generate new tokens
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.id)}
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
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

    async def request_password_reset(self, email: str) -> bool:
        """Request password reset."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()
        
        # Always return success to prevent email enumeration
        if not user:
            return True

        # Generate reset token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS),
        )
        
        self.db.add(reset_token)
        await self.db.commit()
        
        # In production, send email with reset link
        # For now, return the token (development only!)
        return True

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using token."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        result = await self.db.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.token_hash == token_hash,
                    PasswordResetToken.is_used == False,
                    PasswordResetToken.expires_at > datetime.now(timezone.utc),
                )
            )
        )
        reset_token = result.scalar_one_or_none()
        
        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Update password
        user = reset_token.user
        user.password_hash = get_password_hash(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        
        # Mark token as used
        reset_token.is_used = True
        reset_token.used_at = datetime.now(timezone.utc)
        
        # Invalidate all sessions
        await self.logout_all_sessions(user.id)
        
        await self.db.commit()
        
        return True

    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> bool:
        """Change user password."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        user.password_hash = get_password_hash(new_password)
        
        await self.logout_all_sessions(user_id)
        
        await self.db.commit()
        
        return True

    # ============================================================
    # Admin Methods
    # ============================================================

    async def get_pending_users(self) -> list[User]:
        """Get all users with pending status."""
        result = await self.db.execute(
            select(User).where(User.status == EnumUserStatus.PENDING).order_by(User.created_at.desc())
        )
        return result.scalars().all()

    async def get_all_users(self, status_filter: Optional[str] = None, limit: int = 50, offset: int = 0) -> tuple[list[User], int]:
        """Get all users with optional status filter."""
        query = select(User)
        
        if status_filter:
            query = query.where(User.status == status_filter)
        
        # Get total count
        count_query = select(User)
        if status_filter:
            count_query = count_query.where(User.status == status_filter)
        
        from sqlalchemy import func
        count_result = await self.db.execute(select(func.count()).select_from(count_query.subquery()))
        total = count_result.scalar() or 0
        
        # Get paginated results
        query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        
        return result.scalars().all(), total

    async def approve_user(self, user_id: UUID, admin_id: UUID) -> User:
        """Approve a pending user."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.status != EnumUserStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User is not in pending status. Current status: {user.status}"
            )
        
        # Approve user
        user.status = EnumUserStatus.ACTIVE
        user.approved_by = admin_id
        user.approved_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user

    async def reject_user(self, user_id: UUID, admin_id: UUID, reason: Optional[str] = None) -> User:
        """Reject a pending user."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.status != EnumUserStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User is not in pending status. Current status: {user.status}"
            )
        
        # Reject user
        user.status = EnumUserStatus.REJECTED
        user.approved_by = admin_id
        user.approved_at = datetime.now(timezone.utc)
        user.rejection_reason = reason
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user

    async def suspend_user(self, user_id: UUID, admin_id: UUID, reason: Optional[str] = None) -> User:
        """Suspend an active user."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.status == EnumUserStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already suspended"
            )
        
        # Suspend user
        user.status = EnumUserStatus.SUSPENDED
        user.suspended_reason = reason
        
        # Invalidate all sessions
        await self.logout_all_sessions(user_id)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user

    async def reactivate_user(self, user_id: UUID, admin_id: UUID) -> User:
        """Reactivate a suspended user."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.status != EnumUserStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not suspended"
            )
        
        # Reactivate user
        user.status = EnumUserStatus.ACTIVE
        user.suspended_reason = None
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user


class RateLimiter:
    """Rate limiter using Redis."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window: int
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit.
        Returns (is_allowed, remaining)
        """
        try:
            current = self.redis.get(key)
            if current is None:
                self.redis.setex(key, window, 1)
                return True, limit - 1
            
            current = int(current)
            if current >= limit:
                return False, 0
            
            self.redis.incr(key)
            return True, limit - current - 1
        except Exception:
            # If Redis is down, allow request
            return True, limit

    async def get_client_ip(self, request: Request) -> str:
        """Get client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class AuthRateLimiter:
    """Rate limiter specifically for auth endpoints."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_login_rate_limit(self, email: str) -> bool:
        """Check if login attempts are within limit."""
        # Rate limit: 5 attempts per minute, 20 per hour
        email_hash = hashlib.sha256(email.encode()).hexdigest()[:16]
        
        minute_key = f"rate:login:min:{email_hash}"
        hour_key = f"rate:login:hour:{email_hash}"
        
        # Check minute limit
        is_allowed, remaining = await self._check_key(minute_key, 5, 60)
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please wait 1 minute.",
                headers={"Retry-After": "60"}
            )
        
        # Check hour limit
        is_allowed, remaining = await self._check_key(hour_key, 20, 3600)
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
                headers={"Retry-After": "3600"}
            )
        
        return True

    async def _check_key(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Check a specific rate limit key."""
        try:
            current = self.redis.get(key)
            if current is None:
                self.redis.setex(key, window, 1)
                return True, limit - 1
            
            current = int(current)
            if current >= limit:
                return False, 0
            
            self.redis.incr(key)
            return True, limit - current - 1
        except Exception:
            return True, limit


class SessionManager:
    """Manages session activity and timeout."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_session_activity(self, user_id: UUID, token: str) -> bool:
        """Check if session is active and not timed out due to inactivity."""
        from datetime import datetime, timezone, timedelta
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        result = await self.db.execute(
            select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.token_hash == token_hash,
                    UserSession.is_active == True,
                )
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return False
        
        now = datetime.now(timezone.utc)
        inactive_duration = now - session.last_activity_at
        timeout = timedelta(minutes=settings.INACTIVITY_TIMEOUT_MINUTES)
        
        if inactive_duration > timeout:
            session.is_active = False
            await self.db.commit()
            return False
        
        return True

    async def update_session_activity(self, user_id: UUID, token: str) -> bool:
        """Update session last activity timestamp."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        result = await self.db.execute(
            select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.token_hash == token_hash,
                )
            )
        )
        session = result.scalar_one_or_none()
        
        if session:
            session.last_activity_at = datetime.now(timezone.utc)
            await self.db.commit()
            return True
        
        return False

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired and inactive sessions. Returns count of cleaned sessions."""
        from datetime import datetime, timezone, timedelta
        
        timeout = timedelta(minutes=settings.INACTIVITY_TIMEOUT_MINUTES)
        cutoff_time = datetime.now(timezone.utc) - timeout
        
        result = await self.db.execute(
            select(UserSession).where(
                or_(
                    UserSession.expires_at < datetime.now(timezone.utc),
                    UserSession.last_activity_at < cutoff_time,
                    UserSession.is_active == False,
                )
            )
        )
        sessions = result.scalars().all()
        
        count = 0
        for session in sessions:
            await self.db.delete(session)
            count += 1
        
        if count > 0:
            await self.db.commit()
        
        return count

    async def get_active_sessions(self, user_id: UUID) -> list[dict]:
        """Get all active sessions for a user."""
        result = await self.db.execute(
            select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(timezone.utc),
                )
            )
        )
        sessions = result.scalars().all()
        
        return [
            {
                "id": str(s.id),
                "ip_address": s.ip_address,
                "user_agent": s.user_agent,
                "created_at": s.created_at.isoformat(),
                "last_activity_at": s.last_activity_at.isoformat(),
                "expires_at": s.expires_at.isoformat(),
            }
            for s in sessions
        ]
