"""Session management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from core.security import get_current_user, TokenData
from services.auth_service import SessionManager

router = APIRouter(prefix="/sessions", tags=["Session Management"])


@router.get("/me")
async def get_my_sessions(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's active sessions."""
    session_manager = SessionManager(db)
    sessions = await session_manager.get_active_sessions(current_user.user_id)
    return {"sessions": sessions}


@router.post("/heartbeat")
async def session_heartbeat(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update session activity to prevent timeout."""
    from fastapi import Request
    import hashlib
    
    auth_header = Request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    
    token = auth_header.replace("Bearer ", "")
    session_manager = SessionManager(db)
    
    is_valid = await session_manager.check_session_activity(current_user.user_id, token)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired due to inactivity",
            headers={"X-Session-Expired": "true"},
        )
    
    await session_manager.update_session_activity(current_user.user_id, token)
    
    return {"status": "active", "message": "Session activity updated"}


@router.delete("/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a specific session."""
    from uuid import UUID
    from sqlalchemy import select, and_
    from models.auth_models import UserSession
    
    result = await db.execute(
        select(UserSession).where(
            and_(
                UserSession.id == UUID(session_id),
                UserSession.user_id == current_user.user_id,
            )
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    session.is_active = False
    await db.commit()
    
    return {"message": "Session revoked successfully"}


@router.delete("")
async def revoke_all_sessions(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all user sessions (logout from all devices)."""
    session_manager = SessionManager(db)
    count = await session_manager.logout_all_sessions(current_user.user_id)
    
    return {"message": f"Revoked {count} sessions"}


@router.get("/activity")
async def get_session_activity(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get session activity status including inactivity timeout info."""
    from core.config import get_settings
    from datetime import datetime, timezone
    
    settings = get_settings()
    session_manager = SessionManager(db)
    sessions = await session_manager.get_active_sessions(current_user.user_id)
    
    return {
        "inactivity_timeout_minutes": settings.INACTIVITY_TIMEOUT_MINUTES,
        "session_check_interval_minutes": settings.SESSION_CHECK_INTERVAL_MINUTES,
        "active_sessions": len(sessions),
        "sessions": sessions,
    }