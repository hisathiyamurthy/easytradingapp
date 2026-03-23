"""Authentication endpoints including registration and admin APIs."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import get_db
from models.auth_models import User
from core.security import get_current_user, require_role, TokenData
from services.auth_service import AuthService
from schemas.auth_schemas import (
    UserRegistration,
    UserLogin,
    LoginResponse,
    UserResponse,
    RegistrationResponse,
    UserApprovalRequest,
    PendingUserResponse,
    UserListResponse,
    ApprovalResponse,
)
from schemas.enums import UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


async def get_client_ip(request: Request) -> str:
    """Get client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def get_current_admin_user(
    current_user: TokenData = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get current admin user with full user data."""
    from models.auth_models import User
    
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
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
    )


# ============================================================
# Registration Endpoints
# ============================================================

@router.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    user_data: UserRegistration,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.
    
    The account will be created with 'pending' status and require admin approval
    before the user can log in.
    
    Rate limited: 5 registrations per hour per IP.
    """
    # Apply rate limiting for registration
    ip = await get_client_ip(request)
    redis_client = None
    try:
        from database.session import get_redis_client
        redis_client = get_redis_client()
    except Exception:
        pass
    
    if redis_client:
        import hashlib
        rate_key = f"rate_register:{hashlib.md5(ip.encode()).hexdigest()}"
        
        try:
            current = redis_client.get(rate_key)
            if current and int(current) >= 5:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many registration attempts. Please try again later."
                )
        except HTTPException:
            raise
        except Exception:
            pass
    
    auth_service = AuthService(db)
    
    user = await auth_service.register_user(
        user_data=user_data,
        ip_address=ip,
        user_agent=request.headers.get("User-Agent"),
    )
    
    # Update rate limit
    if redis_client:
        try:
            redis_client.incr(rate_key)
            redis_client.expire(rate_key, 3600)  # 1 hour
        except Exception:
            pass
    
    return RegistrationResponse(
        message="Registration successful. Your account is pending approval by an administrator.",
        user_id=user.id,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return access tokens."""
    auth_service = AuthService(db)
    
    ip = await get_client_ip(request)
    
    try:
        result = await auth_service.authenticate_user(
            email=credentials.email,
            password=credentials.password,
            ip_address=ip,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.exception("Login error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


# ============================================================
# Forgot Password
# ============================================================

@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Request password reset for a user.
    
    Generates a reset token and returns it (for demo purposes).
    In production, this would send an email.
    """
    import secrets
    
    email = body.get('email', '')
    
    if not email:
        return {"message": "If an account exists with this email, password reset instructions have been sent."}
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.email == email.lower())
    )
    user = result.scalars().first()
    
    if user:
        # Generate reset token (in production, send via email)
        reset_token = secrets.token_urlsafe(32)
        
        # Store token with expiry (1 hour)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.commit()
        
        # Return token for demo purposes
        return {
            "message": "Password reset instructions have been sent to your email.",
            "reset_token": reset_token,  # For demo: remove in production
            "demo": True  # Indicates this is demo mode
        }
    
    # Always return success to prevent email enumeration
    return {"message": "If an account exists with this email, password reset instructions have been sent."}


@router.post("/reset-password")
async def reset_password(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using the token sent to user's email.
    """
    from datetime import datetime
    
    token = body.get('token', '')
    new_password = body.get('new_password', '')
    confirm_password = body.get('confirm_password', '')
    
    if not token or not new_password:
        return {"detail": "Token and new password are required"}, 400
    
    if new_password != confirm_password:
        return {"detail": "Passwords do not match"}, 400
    
    if len(new_password) < 8:
        return {"detail": "Password must be at least 8 characters"}, 400
    
    # Find user with this token
    result = await db.execute(
        select(User).where(User.reset_token == token)
    )
    user = result.scalars().first()
    
    if not user:
        return {"detail": "Invalid or expired reset token"}, 400
    
    # Check if token is expired
    if user.reset_token_expires and user.reset_token_expires < datetime.now(timezone.utc):
        return {"detail": "Reset token has expired"}, 400
    
    # Update password
    from core.security import get_password_hash
    user.password_hash = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.commit()
    
    return {"message": "Password has been reset successfully. You can now log in."}


# Admin Endpoints (Admin Only)
# ============================================================

@router.get("/admin/pending-users", response_model=list[PendingUserResponse])
async def get_pending_users(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_admin_user),
):
    """Get all pending user registrations. Admin only."""
    auth_service = AuthService(db)
    users = await auth_service.get_pending_users()
    return users


@router.get("/admin/users", response_model=UserListResponse)
async def get_all_users(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_admin_user),
):
    """Get all users with optional status filter. Admin only."""
    auth_service = AuthService(db)
    users, total = await auth_service.get_all_users(
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    
    # Get pending count
    pending_users = await auth_service.get_pending_users()
    
    return UserListResponse(
        users=users,
        total=total,
        pending_count=len(pending_users),
    )


@router.post("/admin/users/{user_id}/approve", response_model=ApprovalResponse)
async def approve_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_admin_user),
):
    """Approve a pending user. Admin only."""
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.approve_user(user_id, current_user.id)
        
        return ApprovalResponse(
            success=True,
            message="User has been approved successfully.",
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve user: {str(e)}"
        )


@router.post("/admin/users/{user_id}/reject", response_model=ApprovalResponse)
async def reject_user(
    user_id: UUID,
    request: UserApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_admin_user),
):
    """Reject a pending user. Admin only."""
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.reject_user(user_id, current_user.id, request.reason)
        
        return ApprovalResponse(
            success=True,
            message="User has been rejected.",
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject user: {str(e)}"
        )


@router.post("/admin/users/{user_id}/suspend", response_model=ApprovalResponse)
async def suspend_user(
    user_id: UUID,
    request: UserApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_admin_user),
):
    """Suspend an active user. Admin only."""
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.suspend_user(user_id, current_user.id, request.reason)
        
        return ApprovalResponse(
            success=True,
            message="User has been suspended.",
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to suspend user: {str(e)}"
        )


@router.post("/admin/users/{user_id}/reactivate", response_model=ApprovalResponse)
async def reactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_admin_user),
):
    """Reactivate a suspended user. Admin only."""
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.reactivate_user(user_id, current_user.id)
        
        return ApprovalResponse(
            success=True,
            message="User has been reactivated.",
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reactivate user: {str(e)}"
        )
