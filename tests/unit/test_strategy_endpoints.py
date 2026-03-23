"""Unit tests for strategy endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

import sys
sys.path.insert(0, 'backend')

from api.v1.endpoints.strategy_endpoints import (
    create_strategy,
    list_strategies,
    get_strategy,
    update_strategy,
    delete_strategy,
    activate_strategy,
    deactivate_strategy,
)
from schemas.strategy_schemas import StrategyCreate, StrategyUpdate


class TestStrategyEndpoints:
    """Tests for strategy API endpoints."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def mock_current_user(self):
        """Create mock current user."""
        from core.security import TokenData
        return TokenData(
            user_id=uuid4(),
            email="test@example.com",
            role="trader"
        )

    @pytest.fixture
    def mock_strategy(self):
        """Create mock strategy object."""
        strategy = MagicMock()
        strategy.id = uuid4()
        strategy.user_id = uuid4()
        strategy.name = "Test Strategy"
        strategy.description = "A test strategy"
        strategy.strategy_type = "momentum"
        strategy.status = "stopped"
        strategy.is_active = True
        strategy.created_at = datetime.utcnow()
        strategy.updated_at = datetime.utcnow()
        return strategy

    @pytest.mark.asyncio
    async def test_create_strategy_success(self, mock_db, mock_current_user):
        """Test successful strategy creation."""
        strategy_data = StrategyCreate(
            name="Test Strategy",
            description="A test strategy",
            strategy_type="momentum",
            is_paper_trading=True,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch('api.v1.endpoints.strategy_endpoints.Strategy') as MockStrategy:
            mock_strategy = MagicMock()
            mock_strategy.id = uuid4()
            MockStrategy.return_value = mock_strategy

            result = await create_strategy(
                strategy_data=strategy_data,
                db=mock_db,
                current_user=mock_current_user,
            )

            mock_db.add.assert_called()
            mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_strategy_duplicate_name(self, mock_db, mock_current_user, mock_strategy):
        """Test creating strategy with duplicate name fails."""
        strategy_data = StrategyCreate(
            name="Existing Strategy",
            description="A test strategy",
            strategy_type="momentum",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_strategy
        mock_db.execute.return_value = mock_result

        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await create_strategy(
                strategy_data=strategy_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_list_strategies(self, mock_db, mock_current_user, mock_strategy):
        """Test listing strategies."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_strategy]
        mock_db.execute.return_value = mock_result

        result = await list_strategies(
            db=mock_db,
            current_user=mock_current_user,
        )

        assert result.total >= 0

    @pytest.mark.asyncio
    async def test_get_strategy_not_found(self, mock_db, mock_current_user):
        """Test getting non-existent strategy."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_strategy(
                strategy_id=uuid4(),
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_strategy_not_found(self, mock_db, mock_current_user):
        """Test updating non-existent strategy."""
        strategy_data = StrategyUpdate(
            name="Updated Name",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await update_strategy(
                strategy_id=uuid4(),
                strategy_data=strategy_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_running_strategy_fails(self, mock_db, mock_current_user, mock_strategy):
        """Test updating a running strategy fails."""
        mock_strategy.status = "running"
        strategy_data = StrategyUpdate(
            name="Updated Name",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_strategy
        mock_db.execute.return_value = mock_result

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await update_strategy(
                strategy_id=mock_strategy.id,
                strategy_data=strategy_data,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400
        assert "running" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_delete_running_strategy_fails(self, mock_db, mock_current_user, mock_strategy):
        """Test deleting a running strategy fails."""
        mock_strategy.status = "running"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_strategy
        mock_db.execute.return_value = mock_result

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await delete_strategy(
                strategy_id=mock_strategy.id,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_activate_strategy_not_found(self, mock_db, mock_current_user):
        """Test activating non-existent strategy."""
        from schemas.strategy_schemas import StrategyActivateRequest
        
        request = StrategyActivateRequest()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await activate_strategy(
                strategy_id=uuid4(),
                request=request,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_deactivate_strategy_not_running(self, mock_db, mock_current_user, mock_strategy):
        """Test deactivating a non-running strategy fails."""
        mock_strategy.status = "stopped"
        
        from schemas.strategy_schemas import StrategyDeactivateRequest
        request = StrategyDeactivateRequest()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_strategy
        mock_db.execute.return_value = mock_result

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await deactivate_strategy(
                strategy_id=mock_strategy.id,
                request=request,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert exc_info.value.status_code == 400


class TestStrategyValidation:
    """Tests for strategy validation logic."""

    def test_strategy_create_validation(self):
        """Test StrategyCreate schema validation."""
        strategy = StrategyCreate(
            name="Test Strategy",
            description="A test",
            strategy_type="momentum",
        )
        
        assert strategy.name == "Test Strategy"
        assert strategy.strategy_type == "momentum"

    def test_strategy_update_validation(self):
        """Test StrategyUpdate schema validation."""
        strategy = StrategyUpdate(
            name="Updated Name",
        )
        
        assert strategy.name == "Updated Name"

    def test_invalid_strategy_type(self):
        """Test invalid strategy type raises error."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            StrategyCreate(
                name="Test",
                strategy_type="invalid_type",
            )
