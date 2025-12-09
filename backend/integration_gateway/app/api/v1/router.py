"""Main API router for v1."""

from fastapi import APIRouter
from app.api.v1.endpoints import gateway, auth

api_router = APIRouter()

api_router.include_router(
    gateway.router,
    tags=["gateway"],
)

api_router.include_router(
    auth.router,
    tags=["auth"],
)

