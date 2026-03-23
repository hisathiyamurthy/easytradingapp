from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from enum import Enum

from core.config import get_settings
from core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


class TokenData:
    """JWT token payload."""
    def __init__(self, user_id: UUID, email: str, role: UserRole):
        self.user_id = user_id
        self.email = email
        self.role = role


class TokenBlacklist:
    """Token blacklist manager using Redis."""
    
    def __init__(self):
        self._redis = None
    
    def _get_redis(self):
        if self._redis is None:
            from database.session import get_redis_client
            self._redis = get_redis_client()
        return self._redis
    
    def _get_token_key(self, token: str) -> str:
        """Generate Redis key for token."""
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return f"token_blacklist:{token_hash}"
    
    def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        redis_client = self._get_redis()
        if not redis_client:
            return False
        
        try:
            key = self._get_token_key(token)
            return redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
            return False
    
    def add_to_blacklist(self, token: str, expires_in_seconds: int) -> bool:
        """Add token to blacklist."""
        redis_client = self._get_redis()
        if not redis_client:
            logger.warning("Redis not available, token will not be blacklisted")
            return False
        
        try:
            key = self._get_token_key(token)
            redis_client.setex(key, expires_in_seconds, "1")
            logger.info(f"Token added to blacklist")
            return True
        except Exception as e:
            logger.error(f"Error adding token to blacklist: {e}")
            return False
    
    def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """Revoke all tokens for a user (logout from all devices)."""
        redis_client = self._get_redis()
        if not redis_client:
            return 0
        
        try:
            pattern = f"user_sessions:{user_id}:*"
            keys = redis_client.keys(pattern)
            count = len(keys)
            if keys:
                redis_client.delete(*keys)
            logger.info(f"Revoked {count} sessions for user {user_id}")
            return count
        except Exception as e:
            logger.error(f"Error revoking user tokens: {e}")
            return 0


_token_blacklist = None


def get_token_blacklist() -> TokenBlacklist:
    """Get token blacklist instance."""
    global _token_blacklist
    if _token_blacklist is None:
        _token_blacklist = TokenBlacklist()
    return _token_blacklist


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token."""
    blacklist = get_token_blacklist()
    
    if blacklist.is_blacklisted(token):
        logger.warning("Attempted to use blacklisted token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        token_type = payload.get("type")
        if token_type not in ["access", "refresh"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role", "trader")
        
        if user_id is None or email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return TokenData(UUID(user_id), email, UserRole(role))
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current authenticated user from JWT token."""
    return decode_token(credentials.credentials)


def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """Get current authenticated user and verify session is active (not timed out)."""
    return decode_token(credentials.credentials)


def require_role(allowed_roles: list[UserRole]):
    """Dependency factory to require specific roles."""
    async def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if current_user.role not in allowed_roles:
            logger.warning(f"User {current_user.user_id} denied access - role {current_user.role} not in {allowed_roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


def require_admin():
    """Require admin role."""
    return require_role([UserRole.ADMIN])


def require_trader():
    """Require trader or admin role."""
    return require_role([UserRole.TRADER, UserRole.ADMIN])