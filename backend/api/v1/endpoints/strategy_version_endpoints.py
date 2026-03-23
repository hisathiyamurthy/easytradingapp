"""Strategy version API endpoints."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from core.security import get_current_user, TokenData, require_trader
from services.strategy_version_service import StrategyVersionService

router = APIRouter(prefix="/strategies/{strategy_id}/versions", tags=["Strategy Version History"])


class StrategyVersionResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    version: int
    name: str
    description: Optional[str]
    strategy_type: str
    parameters: dict
    entry_conditions: dict
    exit_conditions: dict
    change_summary: Optional[str]
    created_by: UUID
    created_at: str

    class Config:
        from_attributes = True


class VersionListResponse(BaseModel):
    versions: List[StrategyVersionResponse]
    total: int


class VersionCompareResponse(BaseModel):
    version1: dict
    version2: dict
    changes: dict


class RollbackRequest(BaseModel):
    change_summary: str = "Rolled back to previous version"


@router.get("", response_model=VersionListResponse)
async def get_strategy_versions(
    strategy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Get all versions of a strategy."""
    version_service = StrategyVersionService(db)
    versions = await version_service.get_versions(strategy_id)
    
    return VersionListResponse(
        versions=[
            StrategyVersionResponse(
                id=v.id,
                strategy_id=v.strategy_id,
                version=v.version,
                name=v.name,
                description=v.description,
                strategy_type=v.strategy_type,
                parameters=v.parameters,
                entry_conditions=v.entry_conditions,
                exit_conditions=v.exit_conditions,
                change_summary=v.change_summary,
                created_by=v.created_by,
                created_at=v.created_at.isoformat(),
            )
            for v in versions
        ],
        total=len(versions),
    )


@router.get("/{version}", response_model=StrategyVersionResponse)
async def get_strategy_version(
    strategy_id: UUID,
    version: int,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Get a specific version of a strategy."""
    version_service = StrategyVersionService(db)
    v = await version_service.get_version(strategy_id, version)
    
    if not v:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found",
        )
    
    return StrategyVersionResponse(
        id=v.id,
        strategy_id=v.strategy_id,
        version=v.version,
        name=v.name,
        description=v.description,
        strategy_type=v.strategy_type,
        parameters=v.parameters,
        entry_conditions=v.entry_conditions,
        exit_conditions=v.exit_conditions,
        change_summary=v.change_summary,
        created_by=v.created_by,
        created_at=v.created_at.isoformat(),
    )


@router.get("/latest", response_model=StrategyVersionResponse)
async def get_latest_version(
    strategy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Get the latest version of a strategy."""
    version_service = StrategyVersionService(db)
    v = await version_service.get_latest_version(strategy_id)
    
    if not v:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No versions found",
        )
    
    return StrategyVersionResponse(
        id=v.id,
        strategy_id=v.strategy_id,
        version=v.version,
        name=v.name,
        description=v.description,
        strategy_type=v.strategy_type,
        parameters=v.parameters,
        entry_conditions=v.entry_conditions,
        exit_conditions=v.exit_conditions,
        change_summary=v.change_summary,
        created_by=v.created_by,
        created_at=v.created_at.isoformat(),
    )


@router.post("", response_model=StrategyVersionResponse)
async def create_strategy_version(
    strategy_id: UUID,
    change_summary: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Create a new version of a strategy (snapshot)."""
    version_service = StrategyVersionService(db)
    
    try:
        v = await version_service.create_version(
            strategy_id=strategy_id,
            user_id=current_user.user_id,
            change_summary=change_summary,
        )
        
        return StrategyVersionResponse(
            id=v.id,
            strategy_id=v.strategy_id,
            version=v.version,
            name=v.name,
            description=v.description,
            strategy_type=v.strategy_type,
            parameters=v.parameters,
            entry_conditions=v.entry_conditions,
            exit_conditions=v.exit_conditions,
            change_summary=v.change_summary,
            created_by=v.created_by,
            created_at=v.created_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/rollback/{version}", response_model=StrategyVersionResponse)
async def rollback_to_version(
    strategy_id: UUID,
    version: int,
    request: RollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Rollback strategy to a previous version."""
    version_service = StrategyVersionService(db)
    
    try:
        strategy = await version_service.rollback_to_version(
            strategy_id=strategy_id,
            version=version,
            user_id=current_user.user_id,
        )
        
        latest = await version_service.get_latest_version(strategy_id)
        
        return StrategyVersionResponse(
            id=latest.id,
            strategy_id=latest.strategy_id,
            version=latest.version,
            name=latest.name,
            description=latest.description,
            strategy_type=latest.strategy_type,
            parameters=latest.parameters,
            entry_conditions=latest.entry_conditions,
            exit_conditions=latest.exit_conditions,
            change_summary=latest.change_summary,
            created_by=latest.created_by,
            created_at=latest.created_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/compare/{version1}/{version2}", response_model=VersionCompareResponse)
async def compare_versions(
    strategy_id: UUID,
    version1: int,
    version2: int,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Compare two versions of a strategy."""
    version_service = StrategyVersionService(db)
    
    try:
        result = await version_service.compare_versions(
            strategy_id=strategy_id,
            version1=version1,
            version2=version2,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )