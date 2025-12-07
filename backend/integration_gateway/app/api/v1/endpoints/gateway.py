"""Gateway endpoints that proxy to internal services."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()

router = APIRouter()


@router.post("/generate/test-case")
async def generate_test_case_proxy(request: Request):
    """Proxy to core-agent-service test case generation."""
    try:
        body = await request.body()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.CORE_AGENT_URL}/api/v1/generate/test-case",
                content=body,
                headers=dict(request.headers),
                timeout=30.0,
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except Exception as e:
        logger.error("Failed to proxy request", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task_status_proxy(task_id: str, request: Request):
    """Proxy to core-agent-service task status."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.CORE_AGENT_URL}/api/v1/tasks/{task_id}",
                headers=dict(request.headers),
                timeout=10.0,
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except Exception as e:
        logger.error("Failed to proxy request", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse/openapi")
async def parse_openapi_proxy(request: Request):
    """Proxy to spec-parser-service."""
    try:
        form = await request.form()
        
        async with httpx.AsyncClient() as client:
            files = {"file": (form["file"].filename, await form["file"].read())}
            response = await client.post(
                f"{settings.SPEC_PARSER_URL}/api/v1/parse/openapi",
                files=files,
                timeout=30.0,
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except Exception as e:
        logger.error("Failed to proxy request", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/code")
async def generate_code_proxy(request: Request):
    """Proxy to code-generator-service."""
    try:
        body = await request.body()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.CODE_GENERATOR_URL}/api/v1/generate/code",
                content=body,
                headers=dict(request.headers),
                timeout=30.0,
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except Exception as e:
        logger.error("Failed to proxy request", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize/coverage")
async def optimize_coverage_proxy(request: Request):
    """Proxy to test-optimizer-service."""
    try:
        body = await request.body()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.TEST_OPTIMIZER_URL}/api/v1/optimize/coverage",
                content=body,
                headers=dict(request.headers),
                timeout=60.0,
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except Exception as e:
        logger.error("Failed to proxy request", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

