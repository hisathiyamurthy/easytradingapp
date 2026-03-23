"""OAuth2 authentication endpoints."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from core.config import get_settings
from services.oauth_service import OAuth2Service, OAuth2GoogleCallback

router = APIRouter(prefix="/oauth", tags=["OAuth2 Authentication"])
settings = get_settings()


class GoogleLoginRequest(BaseModel):
    google_token: str


class GoogleAuthUrlResponse(BaseModel):
    authorization_url: str
    state: str


@router.post("/google/login", status_code=status.HTTP_200_OK)
async def google_login(
    request: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login or register using Google OAuth2 token."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Please contact administrator.",
        )
    
    oauth_service = OAuth2Service(db)
    
    try:
        result = await oauth_service.authenticate_google(request.google_token)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get("/google/auth-url", response_model=GoogleAuthUrlResponse)
async def get_google_auth_url(
    redirect_uri: str = Query(...),
):
    """Get Google OAuth2 authorization URL."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Please contact administrator.",
        )
    
    state = secrets.token_urlsafe(32)
    
    auth_url = await OAuth2GoogleCallback.get_authorization_url(
        client_id=settings.GOOGLE_CLIENT_ID,
        redirect_uri=redirect_uri,
        state=state,
    )
    
    return GoogleAuthUrlResponse(
        authorization_url=auth_url,
        state=state,
    )


@router.post("/google/callback")
async def google_callback(
    code: str = Query(...),
    redirect_uri: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth2 callback."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Please contact administrator.",
        )
    
    try:
        token_data = await OAuth2GoogleCallback.exchange_code_for_token(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            code=code,
            redirect_uri=redirect_uri,
        )
        
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token",
            )
        
        oauth_service = OAuth2Service(db)
        result = await oauth_service.authenticate_google(access_token)
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/google/status")
async def google_oauth_status():
    """Check if Google OAuth is configured."""
    is_configured = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    return {
        "enabled": is_configured,
        "provider": "google" if is_configured else None,
    }
