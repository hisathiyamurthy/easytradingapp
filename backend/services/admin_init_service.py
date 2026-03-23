"""Service for initializing default admin user on application startup."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.auth_models import User
from schemas.enums import UserRole, UserStatus
from core.security import get_password_hash

logger = logging.getLogger(__name__)


async def create_default_admin(db: AsyncSession) -> bool:
    """
    Check if admin exists and create default admin if not.
    
    Reads from environment variables:
    - ADMIN_EMAIL: Email for admin account
    - ADMIN_PASSWORD: Password for admin account
    
    Returns True if admin was created, False if already exists.
    """
    import os
    
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    
    if not admin_email or not admin_password:
        logger.warning(
            "ADMIN_EMAIL or ADMIN_PASSWORD not set. "
            "Skipping default admin creation."
        )
        return False
    
    # Check if admin already exists
    result = await db.execute(
        select(User).where(User.role == UserRole.ADMIN)
    )
    existing_admin = result.scalars().first()
    
    if existing_admin:
        logger.info(f"Admin user already exists: {existing_admin.email}")
        return False
    
    # Create admin user
    admin = User(
        email=admin_email.lower(),
        password_hash=get_password_hash(admin_password),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_verified=True,
    )
    
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    
    logger.info(f"Default admin user created successfully: {admin_email}")
    logger.warning(
        f"SECURITY: Default admin account created. "
        f"Email: {admin_email}. Please change password immediately in production."
    )
    
    return True


async def initialize_admin(db: AsyncSession) -> None:
    """
    Initialize admin user on application startup.
    
    This function is called from the application lifespan event.
    """
    try:
        created = await create_default_admin(db)
        if created:
            logger.info("Admin initialization completed - new admin created")
        else:
            logger.info("Admin initialization completed - admin already exists")
    except Exception as e:
        logger.error(f"Failed to initialize admin: {e}")
        # Don't raise - admin creation failure shouldn't prevent app startup
        # The system can still function with manually created admins
        logger.warning("Application continuing without default admin")
