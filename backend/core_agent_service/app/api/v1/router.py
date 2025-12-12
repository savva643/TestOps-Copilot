"""Main API router for v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import test_generation, tasks, gitlab_tasks, export

api_router = APIRouter()

api_router.include_router(
    test_generation.router,
    prefix="/generate",
    tags=["test-generation"],
)

api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["tasks"],
)

api_router.include_router(
    gitlab_tasks.router,
    prefix="/gitlab",
    tags=["gitlab"],
)

api_router.include_router(
    export.router,
    prefix="/export",
    tags=["export"],
)




