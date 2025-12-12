"""Main API router for v1."""

from fastapi import APIRouter
from app.api.v1.endpoints import gitlab

api_router = APIRouter()

api_router.include_router(
    gitlab.router,
    prefix="/gitlab",
    tags=["gitlab"],
)




