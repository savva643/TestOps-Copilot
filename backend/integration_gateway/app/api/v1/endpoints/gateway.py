"""Gateway endpoints that proxy to internal services."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
import httpx
import structlog

from app.core.config import settings
from app.core.exceptions import ProxyError, ServiceUnavailableError

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
    except httpx.TimeoutException as e:
        logger.error("Timeout proxying request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service timeout",
            details={"service": "core-agent-service", "error": str(e)},
        )
    except httpx.ConnectError as e:
        logger.error("Connection error proxying request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service unavailable",
            details={"service": "core-agent-service", "error": str(e)},
        )
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error proxying request", status_code=e.response.status_code, error=str(e))
        raise ProxyError(
            f"Backend service returned error: {e.response.status_code}",
            details={"service": "core-agent-service", "status_code": e.response.status_code},
        )
    except Exception as e:
        logger.error("Unexpected error proxying request", error=str(e), exc_info=True)
        raise ProxyError(
            "Failed to proxy request",
            details={"service": "core-agent-service", "error": str(e)},
        )


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
    except httpx.TimeoutException as e:
        logger.error("Timeout proxying request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service timeout",
            details={"service": "core-agent-service", "error": str(e)},
        )
    except httpx.ConnectError as e:
        logger.error("Connection error proxying request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service unavailable",
            details={"service": "core-agent-service", "error": str(e)},
        )
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error proxying request", status_code=e.response.status_code, error=str(e))
        raise ProxyError(
            f"Backend service returned error: {e.response.status_code}",
            details={"service": "core-agent-service", "status_code": e.response.status_code},
        )
    except Exception as e:
        logger.error("Unexpected error proxying request", error=str(e), exc_info=True)
        raise ProxyError(
            "Failed to proxy request",
            details={"service": "core-agent-service", "error": str(e)},
        )


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
    except httpx.TimeoutException as e:
        logger.error("Timeout proxying request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service timeout",
            details={"service": "spec-parser-service", "error": str(e)},
        )
    except httpx.ConnectError as e:
        logger.error("Connection error proxying request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service unavailable",
            details={"service": "spec-parser-service", "error": str(e)},
        )
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error proxying request", status_code=e.response.status_code, error=str(e))
        raise ProxyError(
            f"Backend service returned error: {e.response.status_code}",
            details={"service": "spec-parser-service", "status_code": e.response.status_code},
        )
    except Exception as e:
        logger.error("Unexpected error proxying request", error=str(e), exc_info=True)
        raise ProxyError(
            "Failed to proxy request",
            details={"service": "spec-parser-service", "error": str(e)},
        )


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
    except httpx.TimeoutException as e:
        logger.error("Timeout proxying request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service timeout",
            details={"service": "code-generator-service", "error": str(e)},
        )
    except httpx.ConnectError as e:
        logger.error("Connection error proxying request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service unavailable",
            details={"service": "code-generator-service", "error": str(e)},
        )
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error proxying request", status_code=e.response.status_code, error=str(e))
        raise ProxyError(
            f"Backend service returned error: {e.response.status_code}",
            details={"service": "code-generator-service", "status_code": e.response.status_code},
        )
    except Exception as e:
        logger.error("Unexpected error proxying request", error=str(e), exc_info=True)
        raise ProxyError(
            "Failed to proxy request",
            details={"service": "code-generator-service", "error": str(e)},
        )


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
    except httpx.TimeoutException as e:
        logger.error("Timeout proxying request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service timeout",
            details={"service": "test-optimizer-service", "error": str(e)},
        )
    except httpx.ConnectError as e:
        logger.error("Connection error proxying request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service unavailable",
            details={"service": "test-optimizer-service", "error": str(e)},
        )
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error proxying request", status_code=e.response.status_code, error=str(e))
        raise ProxyError(
            f"Backend service returned error: {e.response.status_code}",
            details={"service": "test-optimizer-service", "status_code": e.response.status_code},
        )
    except Exception as e:
        logger.error("Unexpected error proxying request", error=str(e), exc_info=True)
        raise ProxyError(
            "Failed to proxy request",
            details={"service": "test-optimizer-service", "error": str(e)},
        )

