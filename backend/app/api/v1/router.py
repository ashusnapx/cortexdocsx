"""
WHAT: Versioned API router aggregator.
WHY: Mounts all v1 endpoint routers under /api/v1 prefix. Single point for
     adding new route modules. Versioning enables backward-compatible API evolution.
WHEN: Mounted on the FastAPI app during initialization.
WHERE: backend/app/api/v1/router.py
HOW: APIRouter includes sub-routers with prefix.
ALTERNATIVES CONSIDERED: Flask-style blueprints — not applicable to FastAPI.
TRADEOFFS: Router nesting adds minor routing overhead — negligible.
"""

from fastapi import APIRouter

from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.query import router as query_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(documents_router)
api_v1_router.include_router(query_router)
api_v1_router.include_router(health_router)
