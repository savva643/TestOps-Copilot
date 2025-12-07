"""Main API router for v1."""

from fastapi import APIRouter
from app.api.v1.endpoints import generator

api_router = APIRouter()

api_router.include_router(
    generator.router,
    prefix="/generate",
    tags=["generator"],
)

