"""Strategy version service for managing strategy history."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from models.strategy_version_models import StrategyVersion
from models.strategy_models import Strategy


class StrategyVersionService:
    """Service for managing strategy versions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_version(
        self,
        strategy_id: UUID,
        user_id: UUID,
        change_summary: str,
    ) -> StrategyVersion:
        """Create a new version of a strategy."""
        result = await self.db.execute(
            select(StrategyVersion)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(desc(StrategyVersion.version))
            .limit(1)
        )
        latest_version = result.scalar_one_or_none()

        new_version = (latest_version.version + 1) if latest_version else 1

        strategy_result = await self.db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = strategy_result.scalar_one_or_none()

        if not strategy:
            raise ValueError("Strategy not found")

        version = StrategyVersion(
            strategy_id=strategy_id,
            version=new_version,
            name=strategy.name,
            description=strategy.description,
            strategy_type=strategy.strategy_type,
            parameters=strategy.parameters,
            entry_conditions=strategy.entry_conditions,
            exit_conditions=strategy.exit_conditions,
            change_summary=change_summary,
            created_by=user_id,
        )

        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)

        return version

    async def get_versions(self, strategy_id: UUID) -> List[StrategyVersion]:
        """Get all versions of a strategy."""
        result = await self.db.execute(
            select(StrategyVersion)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(desc(StrategyVersion.version))
        )
        return list(result.scalars().all())

    async def get_version(self, strategy_id: UUID, version: int) -> Optional[StrategyVersion]:
        """Get a specific version of a strategy."""
        result = await self.db.execute(
            select(StrategyVersion).where(
                StrategyVersion.strategy_id == strategy_id,
                StrategyVersion.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_version(self, strategy_id: UUID) -> Optional[StrategyVersion]:
        """Get the latest version of a strategy."""
        result = await self.db.execute(
            select(StrategyVersion)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(desc(StrategyVersion.version))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def rollback_to_version(
        self, strategy_id: UUID, version: int, user_id: UUID
    ) -> Strategy:
        """Rollback a strategy to a previous version."""
        version_result = await self.db.execute(
            select(StrategyVersion).where(
                StrategyVersion.strategy_id == strategy_id,
                StrategyVersion.version == version,
            )
        )
        strategy_version = version_result.scalar_one_or_none()

        if not strategy_version:
            raise ValueError("Version not found")

        strategy_result = await self.db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = strategy_result.scalar_one_or_none()

        if not strategy:
            raise ValueError("Strategy not found")

        strategy.description = strategy_version.description
        strategy.strategy_type = strategy_version.strategy_type
        strategy.parameters = strategy_version.parameters
        strategy.entry_conditions = strategy_version.entry_conditions
        strategy.exit_conditions = strategy_version.exit_conditions

        await self.db.commit()
        await self.db.refresh(strategy)

        await self.create_version(
            strategy_id=strategy_id,
            user_id=user_id,
            change_summary=f"Rolled back to version {version}",
        )

        return strategy

    async def compare_versions(
        self, strategy_id: UUID, version1: int, version2: int
    ) -> dict:
        """Compare two versions of a strategy."""
        v1 = await self.get_version(strategy_id, version1)
        v2 = await self.get_version(strategy_id, version2)

        if not v1 or not v2:
            raise ValueError("One or both versions not found")

        changes = {
            "name_changed": v1.name != v2.name,
            "description_changed": v1.description != v2.description,
            "type_changed": v1.strategy_type != v2.strategy_type,
            "parameters_changed": v1.parameters != v2.parameters,
            "entry_conditions_changed": v1.entry_conditions != v2.entry_conditions,
            "exit_conditions_changed": v1.exit_conditions != v2.exit_conditions,
        }

        return {
            "version1": {
                "version": v1.version,
                "created_at": v1.created_at.isoformat(),
                "change_summary": v1.change_summary,
            },
            "version2": {
                "version": v2.version,
                "created_at": v2.created_at.isoformat(),
                "change_summary": v2.change_summary,
            },
            "changes": changes,
        }
