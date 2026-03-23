"""API Versioning and Deprecation Middleware."""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


API_VERSION = "1.0.0"
DEPRECATED_VERSIONS = ["0.9.0", "0.8.0"]
SUPPORTED_VERSIONS = ["1.0.0", "1.1.0", "2.0.0"]


@dataclass
class DeprecationInfo:
    """Deprecation information for an endpoint."""
    deprecated_since: str
    sunsets: str
    replacement: Optional[str]
    migration_guide: Optional[str]


class DeprecationTracker:
    """Track deprecated API endpoints."""
    
    def __init__(self):
        self._deprecated_endpoints: Dict[str, DeprecationInfo] = {}
    
    def register_deprecation(
        self,
        endpoint: str,
        deprecated_since: str,
        sunsets: str,
        replacement: Optional[str] = None,
        migration_guide: Optional[str] = None,
    ):
        self._deprecated_endpoints[endpoint] = DeprecationInfo(
            deprecated_since=deprecated_since,
            sunsets=sunsets,
            replacement=replacement,
            migration_guide=migration_guide,
        )
    
    def get_deprecation(self, endpoint: str) -> Optional[DeprecationInfo]:
        return self._deprecated_endpoints.get(endpoint)


deprecation_tracker = DeprecationTracker()

deprecation_tracker.register_deprecation(
    "/api/v1/auth/register",
    "1.0.0",
    "2.0.0",
    "/api/v2/auth/register",
    "https://docs.easytradingapp.com/migration/v1-to-v2",
)

deprecation_tracker.register_deprecation(
    "/api/v1/strategies/backtest",
    "1.0.0",
    "1.5.0",
    "/api/v2/backtesting",
    "https://docs.easytradingapp.com/migration/backtest-v2",
)


class APIVersioningMiddleware(BaseHTTPMiddleware):
    """Middleware for API versioning and deprecation warnings."""
    
    def __init__(self, app):
        super().__init__(app)
        self.deprecation_tracker = deprecation_tracker
    
    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        client_version = request.headers.get("X-API-Version", API_VERSION)
        
        response = await call_next(request)
        
        if client_version in DEPRECATED_VERSIONS:
            deprecation = self.deprecation_tracker.get_deprecation(request.url.path)
            
            if deprecation:
                response.headers["Deprecation"] = "true"
                response.headers["Sunset"] = deprecation.sunsets
                
                if deprecation.replacement:
                    response.headers["Link"] = f'<{deprecation.replacement}>; rel="successor-version"'
                
                response.headers["X-API-Deprecation"] = f'version="{client_version}", date="{deprecation.deprecated_since}"'
                
                logger.warning(
                    f"Deprecated API called: {request.url.path} by client version {client_version}"
                )
        
        response.headers["X-API-Version"] = API_VERSION
        response.headers["X-API-Supported-Versions"] = ",".join(SUPPORTED_VERSIONS)
        
        return response


def require_api_version(min_version: str):
    """Dependency to require minimum API version."""
    async def _check_version(request: Request):
        client_version = request.headers.get("X-API-Version", API_VERSION)
        
        if client_version < min_version:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_UPGRADE_REQUIRED,
                detail=f"API version {min_version} or higher required. Current: {client_version}",
                headers={
                    "X-API-Version": API_VERSION,
                    "X-Min-Version": min_version,
                },
            )
    
    return _check_version


class VersionedRouter:
    """Router that supports API versioning."""
    
    def __init__(self, prefix: str = "", version: str = "1.0.0"):
        self.prefix = prefix
        self.version = version
        self._routes: List[dict] = []
    
    def add_route(self, path: str, handler, deprecated: bool = False):
        self._routes.append({
            "path": path,
            "handler": handler,
            "deprecated": deprecated,
        })
    
    def get_routes(self):
        return self._routes