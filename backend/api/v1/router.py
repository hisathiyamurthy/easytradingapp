"""API v1 router - combines all endpoint routers."""
from fastapi import APIRouter

from api.v1.endpoints import (
    strategy_endpoints,
    strategy_instance_endpoints,
    strategy_version_endpoints,
    mfa_endpoints,
    notification_endpoints,
    oauth_endpoints,
    market_endpoints,
    session_endpoints,
    backtest_endpoints,
    auth_endpoints,
    admin_endpoints,
    order_endpoints,
    portfolio_endpoints,
    broker_endpoints,
    risk_endpoints,
    paper_trading_endpoints,
    live_trading_endpoints,
)

api_router = APIRouter()

api_router.include_router(auth_endpoints.router)
api_router.include_router(strategy_endpoints.router)
api_router.include_router(strategy_instance_endpoints.router)
api_router.include_router(strategy_version_endpoints.router)
api_router.include_router(mfa_endpoints.router)
api_router.include_router(notification_endpoints.router)
api_router.include_router(oauth_endpoints.router)
api_router.include_router(market_endpoints.router)
api_router.include_router(session_endpoints.router)
api_router.include_router(backtest_endpoints.router)
api_router.include_router(admin_endpoints.router)
api_router.include_router(order_endpoints.router)
api_router.include_router(portfolio_endpoints.router)
api_router.include_router(broker_endpoints.router)
api_router.include_router(risk_endpoints.router)
api_router.include_router(paper_trading_endpoints.router)
api_router.include_router(live_trading_endpoints.router)
