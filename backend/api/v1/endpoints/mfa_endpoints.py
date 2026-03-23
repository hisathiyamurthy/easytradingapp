"""MFA (Multi-Factor Authentication) API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from core.security import get_current_user, TokenData
from services.totp_service import MFAService
from schemas.auth_schemas import (
    MFASetupResponse,
    MFAVerifyResponse,
    MFAVerifyRequest,
)

router = APIRouter(prefix="/mfa", tags=["Multi-Factor Authentication"])


@router.post("/setup", response_model=MFASetupResponse)
async def setup_mfa(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Initialize MFA setup for the current user."""
    mfa_service = MFAService(db)
    
    try:
        result = await mfa_service.setup_mfa(str(current_user.user_id))
        return MFASetupResponse(
            mfa_enabled=False,
            secret=result["secret"],
            qr_code=result["qr_code_url"],
            message=result["message"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/verify", response_model=MFAVerifyResponse)
async def verify_mfa_code(
    request: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Verify MFA code and enable MFA."""
    mfa_service = MFAService(db)
    
    try:
        await mfa_service.enable_mfa(str(current_user.user_id), request.code)
        return MFAVerifyResponse(
            verified=True,
            message="MFA enabled successfully",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/disable", response_model=MFAVerifyResponse)
async def disable_mfa(
    request: MFAVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Disable MFA for the current user."""
    mfa_service = MFAService(db)
    
    try:
        await mfa_service.disable_mfa(
            str(current_user.user_id),
            request.code,
            "",  # Password would be in request body in production
        )
        return MFAVerifyResponse(
            verified=True,
            message="MFA disabled successfully",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/status", response_model=dict)
async def get_mfa_status(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get MFA status for the current user."""
    mfa_service = MFAService(db)
    
    try:
        return await mfa_service.get_mfa_status(str(current_user.user_id))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
