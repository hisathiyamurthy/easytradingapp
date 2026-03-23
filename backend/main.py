"""FastAPI main application."""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import get_settings, validate_environment, SecretsManager, get_secrets_manager
from sqlalchemy import text
from api.v1.router import api_router
from services.websocket_service import websocket_endpoint

settings = get_settings()
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_notification_migrations(conn):
    """Run migrations for notification_preferences table to add new columns."""
    try:
        columns_to_add = [
            ("telegram_enabled", "BOOLEAN DEFAULT FALSE"),
            ("telegram_chat_id", "VARCHAR(100)"),
            ("telegram_bot_token", "VARCHAR(255)"),
            ("whatsapp_enabled", "BOOLEAN DEFAULT FALSE"),
            ("whatsapp_phone", "VARCHAR(20)"),
            ("whatsapp_webhook_url", "VARCHAR(500)"),
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                result = await conn.execute(text(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'notification_preferences' AND column_name = '{col_name}'
                """))
                if result.fetchone() is None:
                    await conn.execute(text(f"""
                        ALTER TABLE notification_preferences 
                        ADD COLUMN {col_name} {col_type}
                    """))
                    logger.info(f"Migration: Added column {col_name}")
                else:
                    logger.info(f"Migration: Column {col_name} already exists")
            except Exception as e:
                logger.warning(f"Migration error for {col_name}: {e}")
    except Exception as e:
        logger.warning(f"Notification migrations failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info(f"Starting EasyTradingApp v{settings.APP_VERSION}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    missing_secrets = validate_environment()
    if missing_secrets:
        logger.warning(f"Missing secrets: {missing_secrets}")
        if settings.ENVIRONMENT == "production":
            logger.error("Cannot start in production mode with missing secrets!")
            raise RuntimeError(f"Missing required secrets: {missing_secrets}")
    
    secrets_manager = get_secrets_manager()
    if settings.AWS_SECRETS_MANAGER_ENABLED:
        await secrets_manager.load_secrets()
    
    # Create database tables if they don't exist
    try:
        from database.base import Base
        from database.session import engine
        
        # Import all models to ensure they are registered with Base
        # Order matters - models with relationships must be imported after their dependencies
        import models.broker_account_models
        import models.auth_models
        import models.order_models
        import models.strategy_models
        import models.strategy_version_models
        import models.notification_models
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
            
            # Run migrations for new columns
            await run_notification_migrations(conn)
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
    
    # Initialize default admin user
    try:
        from database.session import AsyncSessionLocal
        from services.admin_init_service import initialize_admin
        
        async with AsyncSessionLocal() as db:
            await initialize_admin(db)
    except Exception as e:
        logger.error(f"Failed to initialize admin: {e}")
    
    yield
    
    logger.info("Shutting down EasyTradingApp...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Algorithmic Trading Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5300"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from core.middleware import CorrelationIdMiddleware
app.add_middleware(CorrelationIdMiddleware)

from core.rate_limiter import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "EasyTradingApp API", 
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with dependency verification."""
    health_status = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
    
    try:
        missing = validate_environment()
        if missing:
            health_status["secrets"] = "missing"
            health_status["missing_secrets"] = missing
        else:
            health_status["secrets"] = "configured"
    except Exception as e:
        health_status["secrets"] = f"error: {str(e)}"
        health_status["missing_secrets"] = []
    
    all_healthy = all(v != "error" for v in health_status.values()) and not health_status.get("missing_secrets")
    health_status["status"] = "healthy" if all_healthy else "degraded"
    
    status_code = 200 if all_healthy else 503
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/health/ready")
async def readiness_check():
    """Readiness check - verifies all dependencies are ready."""
    checks = {
        "database": "unknown",
        "redis": "unknown",
    }
    
    try:
        from database.session import get_redis_client
        redis = get_redis_client()
        if redis:
            redis.ping()
            checks["redis"] = "ready"
        else:
            checks["redis"] = "not_configured"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"
    
    is_ready = all(v == "ready" for v in checks.values())
    return JSONResponse(
        content={"ready": is_ready, "checks": checks},
        status_code=200 if is_ready else 503,
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from services.metrics_service import get_metrics_service
    from fastapi.responses import Response
    
    metrics_service = get_metrics_service()
    return Response(
        content=metrics_service.get_metrics(),
        media_type="text/plain",
    )


@app.websocket("/ws")
async def websocket_connect(websocket: WebSocket, token: Optional[str] = None):
    """WebSocket endpoint for real-time updates."""
    await websocket_endpoint(websocket, token)


app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)