"""Main API router for v1."""

from fastapi import APIRouter
from app.api.v1.endpoints import parser

api_router = APIRouter()

api_router.include_router(
    parser.router,
    prefix="/parse",
    tags=["parser"],
)




