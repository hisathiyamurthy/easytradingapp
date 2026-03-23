"""Unit tests for auth service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone, timedelta

import sys
sys.path.insert(0, 'backend')

from services.auth_service import AuthService, RateLimiter, AuthRateLimiter
from core.security import create_access_token, verify_password, get_password_hash
from schemas.auth_schemas import UserCreate
from models.auth_models import User, UserSession


class TestAuthService:
    """Tests for AuthService."""

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
    def auth_service(self, mock_db):
        """Create auth service instance."""
        return AuthService(mock_db)

    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, mock_db):
        """Test successful user registration."""
        user_data = UserCreate(
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User"
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        user = await auth_service.register_user(user_data)

        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, auth_service, mock_db):
        """Test registration with duplicate email fails."""
        user_data = UserCreate(
            email="existing@example.com",
            password="password123",
            first_name="Test",
            last_name="User"
        )

        existing_user = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_db.execute.return_value = mock_result

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register_user(user_data)

        assert exc_info.value.status_code == 400
        assert "already registered" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, mock_db):
        """Test successful user authentication."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "test@example.com"
        user.password_hash = get_password_hash("password123")
        user.failed_login_attempts = 0
        user.is_locked = False
        user.is_active = True
        user.role = MagicMock(value="trader")
        user.last_login_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        with patch('services.auth_service.verify_password', return_value=True):
            with patch('services.auth_service.create_access_token') as mock_access:
                with patch('services.auth_service.create_refresh_token') as mock_refresh:
                    mock_access.return_value = "access_token"
                    mock_refresh.return_value = "refresh_token"

                    result = await auth_service.authenticate_user(
                        "test@example.com",
                        "password123"
                    )

                    assert result.access_token == "access_token"
                    assert result.refresh_token == "refresh_token"

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, auth_service, mock_db):
        """Test authentication with wrong password fails."""
        user = MagicMock()
        user.password_hash = get_password_hash("correct_password")
        user.failed_login_attempts = 0
        user.is_locked = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        with patch('services.auth_service.verify_password', return_value=False):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.authenticate_user(
                    "test@example.com",
                    "wrong_password"
                )

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_authenticate_user_locked_account(self, auth_service, mock_db):
        """Test authentication with locked account fails."""
        user = MagicMock()
        user.password_hash = get_password_hash("password123")
        user.is_locked = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        with patch('services.auth_service.verify_password', return_value=True):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.authenticate_user(
                    "test@example.com",
                    "password123"
                )

            assert exc_info.value.status_code == 423
            assert "locked" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_logout(self, auth_service, mock_db):
        """Test user logout."""
        user_id = uuid4()
        token = "test_token"
        session = MagicMock()
        session.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = session
        mock_db.execute.return_value = mock_result

        result = await auth_service.logout(user_id, token)

        assert result is True
        assert session.is_active is False
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_all_sessions(self, auth_service, mock_db):
        """Test logout all sessions."""
        user_id = uuid4()
        session1 = MagicMock()
        session2 = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [session1, session2]
        mock_db.execute.return_value = mock_result

        count = await auth_service.logout_all_sessions(user_id)

        assert count == 2
        assert session1.is_active is False
        assert session2.is_active is False

    @pytest.mark.asyncio
    async def test_change_password(self, auth_service, mock_db):
        """Test password change."""
        user_id = uuid4()
        user = MagicMock()
        user.password_hash = get_password_hash("old_password")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        with patch('services.auth_service.verify_password', return_value=True):
            result = await auth_service.change_password(
                user_id,
                "old_password",
                "new_password"
            )

            assert result is True
            mock_db.commit.assert_called_once()


class TestRateLimiter:
    """Tests for RateLimiter."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis = MagicMock()
        redis.get = MagicMock(return_value=None)
        redis.setex = MagicMock()
        redis.incr = MagicMock()
        return redis

    @pytest.mark.asyncio
    async def test_check_rate_limit_first_request(self, mock_redis):
        """Test first request has no rate limit."""
        limiter = RateLimiter(mock_redis)
        mock_redis.get.return_value = None

        is_allowed, remaining = await limiter.check_rate_limit("test_key", 10, 60)

        assert is_allowed is True
        assert remaining == 9
        mock_redis.setex.assert_called_once_with("test_key", 60, 1)

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, mock_redis):
        """Test rate limit exceeded."""
        limiter = RateLimiter(mock_redis)
        mock_redis.get.return_value = "10"

        is_allowed, remaining = await limiter.check_rate_limit("test_key", 10, 60)

        assert is_allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_down(self, mock_redis):
        """Test fallback when Redis is down."""
        limiter = RateLimiter(mock_redis)
        mock_redis.get.side_effect = Exception("Redis down")

        is_allowed, remaining = await limiter.check_rate_limit("test_key", 10, 60)

        assert is_allowed is True


class TestPasswordHashing:
    """Tests for password hashing."""

    def test_password_hash_creation(self):
        """Test password hashing creates valid hash."""
        password = "test_password123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)

    def test_different_hashes_for_same_password(self):
        """Test same password creates different hashes due to salt."""
        password = "test_password123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestTokenCreation:
    """Tests for token creation."""

    def test_create_access_token(self):
        """Test access token creation."""
        token = create_access_token({"sub": "user123", "email": "test@example.com"})

        assert token is not None
        assert isinstance(token, str)

    def test_token_contains_expected_data(self):
        """Test token contains expected payload."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        from jose import jwt
        from core.config import get_settings
        settings = get_settings()

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
