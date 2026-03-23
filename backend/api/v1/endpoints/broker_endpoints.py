"""Broker account management API endpoints."""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from core.security import get_current_user, TokenData
from models.broker_account_models import BrokerAccount
from broker_integrations.base import BrokerName

router = APIRouter(prefix="/brokers", tags=["Brokers"])


class BrokerAccountCreate(BaseModel):
    broker_name: str
    account_id: str
    account_name: Optional[str] = None
    encrypted_api_key: str
    encrypted_api_secret: str
    encrypted_api_passphrase: Optional[str] = None
    webhook_url: Optional[str] = None
    is_paper_trading: bool = False


class BrokerAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    webhook_url: Optional[str] = None
    is_active: Optional[bool] = None


class BrokerAccountResponse(BaseModel):
    id: str
    broker_name: str
    account_id: str
    account_name: Optional[str]
    is_paper_trading: bool
    is_active: bool
    last_sync_at: Optional[str]
    health_status: str
    created_at: str

    class Config:
        from_attributes = True


class BrokerConnectionTest(BaseModel):
    broker_name: str
    account_id: str
    api_key: str
    api_secret: str
    api_passphrase: Optional[str] = None


class BrokerCredentialFields(BaseModel):
    """Response with required credential fields for each broker."""
    broker_name: str
    fields: List[dict]


AVAILABLE_BROKERS = {
    "zerodha": {
        "name": "Zerodha",
        "fields": [
            {"name": "api_key", "label": "API Key", "type": "text", "required": True, "placeholder": "Enter API Key"},
            {"name": "api_secret", "label": "API Secret", "type": "password", "required": True, "placeholder": "Enter API Secret"},
            {"name": "totp_key", "label": "TOTP Key", "type": "password", "required": True, "placeholder": "Enter TOTP Key"},
        ]
    },
    "angel_one": {
        "name": "Angel One",
        "fields": [
            {"name": "client_id", "label": "Client ID", "type": "text", "required": True, "placeholder": "Enter Client ID"},
            {"name": "password", "label": "Password", "type": "password", "required": True, "placeholder": "Enter Password"},
            {"name": "totp_key", "label": "TOTP Key", "type": "password", "required": True, "placeholder": "Enter TOTP Key"},
        ]
    },
    "upstox": {
        "name": "Upstox",
        "fields": [
            {"name": "api_key", "label": "API Key", "type": "text", "required": True, "placeholder": "Enter API Key"},
            {"name": "api_secret", "label": "API Secret", "type": "password", "required": True, "placeholder": "Enter API Secret"},
        ]
    },
    "kotak_neo": {
        "name": "Kotak Neo",
        "fields": [
            {"name": "consumer_key", "label": "Consumer Key", "type": "text", "required": True},
            {"name": "consumer_secret", "label": "Consumer Secret", "type": "password", "required": True},
            {"name": "access_token", "label": "Access Token", "type": "password", "required": True},
        ]
    },
}


@router.get("", response_model=List[BrokerAccountResponse])
async def list_broker_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """List all broker accounts for the current user."""
    result = await db.execute(
        select(BrokerAccount).where(BrokerAccount.user_id == current_user.user_id)
    )
    accounts = result.scalars().all()

    return [
        BrokerAccountResponse(
            id=str(a.id),
            broker_name=a.broker_name.value,
            account_id=a.account_id,
            account_name=a.account_name,
            is_paper_trading=a.is_paper_trading,
            is_active=a.is_active,
            last_sync_at=a.last_sync_at.isoformat() if a.last_sync_at else None,
            health_status=a.health_status,
            created_at=a.created_at.isoformat(),
        )
        for a in accounts
    ]


@router.post("", response_model=BrokerAccountResponse, status_code=201)
async def create_broker_account(
    account_data: BrokerAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Add a new broker account."""
    # Validate broker name
    try:
        broker_name = BrokerName(account_data.broker_name.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid broker: {account_data.broker_name}")

    # Create broker account with encrypted credentials using persistent encryption
    from core.encryption import get_encryption_service
    
    try:
        encryption_service = get_encryption_service()
    except ValueError:
        raise HTTPException(
            status_code=500, 
            detail="Encryption service not configured. Set ENCRYPTION_KEY and ENCRYPTION_SALT environment variables."
        )
    
    encrypted_api_key = encryption_service.encrypt(account_data.encrypted_api_key)
    encrypted_api_secret = encryption_service.encrypt(account_data.encrypted_api_secret)
    
    encrypted_passphrase = None
    if account_data.encrypted_api_passphrase:
        encrypted_passphrase = encryption_service.encrypt(account_data.encrypted_api_passphrase)

    account = BrokerAccount(
        user_id=current_user.user_id,
        broker_name=broker_name,
        account_id=account_data.account_id,
        account_name=account_data.account_name,
        encrypted_api_key=encrypted_api_key,
        encrypted_api_secret=encrypted_api_secret,
        encrypted_api_passphrase=encrypted_passphrase if encrypted_passphrase else None,
        webhook_url=account_data.webhook_url,
        is_paper_trading=account_data.is_paper_trading,
        is_active=True,
    )

    db.add(account)
    await db.commit()
    await db.refresh(account)

    return BrokerAccountResponse(
        id=str(account.id),
        broker_name=account.broker_name.value,
        account_id=account.account_id,
        account_name=account.account_name,
        is_paper_trading=account.is_paper_trading,
        is_active=account.is_active,
        last_sync_at=account.last_sync_at.isoformat() if account.last_sync_at else None,
        health_status=account.health_status,
        created_at=account.created_at.isoformat(),
    )


@router.get("/fields", response_model=List[dict])
async def get_broker_fields():
    """Get credential fields required for each broker."""
    return list(AVAILABLE_BROKERS.values())


@router.post("/test-connection")
async def test_broker_connection(
    test_data: BrokerConnectionTest,
):
    """Test broker connection with provided credentials."""
    from services.live_trading_service import MockBroker
    import asyncio
    
    try:
        # Run test with timeout to prevent hanging
        broker = MockBroker()
        
        # Attempt to connect with the provided credentials - with timeout
        try:
            success = await asyncio.wait_for(
                broker.test_connection(
                    api_key=test_data.api_key,
                    api_secret=test_data.api_secret,
                    account_id=test_data.account_id,
                ),
                timeout=10.0  # 10 second timeout
            )
        except asyncio.TimeoutError:
            return {
                "success": False,
                "message": "Connection test timed out. Please try again.",
                "account_id": test_data.account_id,
            }
        
        if success:
            return {
                "success": True,
                "message": f"Successfully connected to {test_data.broker_name}",
                "account_id": test_data.account_id,
            }
        else:
            return {
                "success": False,
                "message": f"Failed to connect to {test_data.broker_name}. Please check your credentials.",
                "account_id": test_data.account_id,
            }
            
    except Exception as e:
        logger.error(f"Broker connection test error: {e}")
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "account_id": test_data.account_id,
        }


@router.get("/{account_id}", response_model=BrokerAccountResponse)
async def get_broker_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get a specific broker account."""
    try:
        account_uuid = UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account ID")

    result = await db.execute(
        select(BrokerAccount).where(
            BrokerAccount.id == account_uuid,
            BrokerAccount.user_id == current_user.user_id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Broker account not found")

    return BrokerAccountResponse(
        id=str(account.id),
        broker_name=account.broker_name.value,
        account_id=account.account_id,
        account_name=account.account_name,
        is_paper_trading=account.is_paper_trading,
        is_active=account.is_active,
        last_sync_at=account.last_sync_at.isoformat() if account.last_sync_at else None,
        health_status=account.health_status,
        created_at=account.created_at.isoformat(),
    )


@router.delete("/{account_id}")
async def delete_broker_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Delete a broker account."""
    try:
        account_uuid = UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account ID")

    result = await db.execute(
        select(BrokerAccount).where(
            BrokerAccount.id == account_uuid,
            BrokerAccount.user_id == current_user.user_id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Broker account not found")

    await db.delete(account)
    await db.commit()

    return {"message": "Broker account deleted successfully"}
