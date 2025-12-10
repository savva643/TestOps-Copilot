"""Gateway endpoints that proxy to internal services."""

from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
import httpx
import structlog
import io
import zipfile
import asyncio

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


@router.websocket("/tasks/ws/{task_id}")
async def task_status_ws(task_id: str, websocket: WebSocket):
    """WebSocket that streams task status by polling core-agent-service."""
    api_key = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")
    if api_key != settings.API_KEY:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    try:
        async with httpx.AsyncClient() as client:
            while True:
                resp = await client.get(
                    f"{settings.CORE_AGENT_URL}/api/v1/tasks/{task_id}",
                    headers={"X-API-Key": settings.API_KEY},
                    timeout=10.0,
                )
                await websocket.send_text(resp.text)

                data = resp.json()
                status = data.get("status", "").upper()
                if status not in ["PENDING", "PROGRESS", "IN_PROGRESS"]:
                    break

                await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        logger.info("Task WS disconnected", task_id=task_id)
    except Exception as e:
        logger.error("Task WS error", task_id=task_id, error=str(e), exc_info=True)
        try:
            await websocket.send_text('{"error":"websocket_error"}')
        except Exception:
            pass
    finally:
        await websocket.close()


@router.get("/tasks")
async def list_tasks_proxy(request: Request):
    """Proxy task list to core-agent-service."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.CORE_AGENT_URL}/api/v1/tasks",
                headers=dict(request.headers),
                params=request.query_params,
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
        try:
            error_detail = e.response.json().get("detail", str(e))
        except:
            error_detail = e.response.text or str(e)
        raise ProxyError(
            f"Ошибка парсинга: {error_detail}",
            details={"service": "spec-parser-service", "status_code": e.response.status_code, "detail": error_detail},
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


@router.get("/artifacts/{task_id}")
async def download_artifacts(task_id: str):
    """
    Return ZIP artifacts for a task (placeholder bundling).

    In production, this should fetch artifacts from storage/code-generator service.
    """
    try:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "README.txt",
                (
                    "TestOps Copilot artifacts\n"
                    f"Task: {task_id}\n"
                    "Contents: sample test file and metadata.\n"
                ),
            )
            zf.writestr(
                "tests/test_sample.py",
                (
                    "import pytest\n\n"
                    "def test_sample():\n"
                    "    assert True\n"
                ),
            )
            zf.writestr(
                "metadata.json",
                '{"task_id": "' + task_id + '", "status": "completed", "note": "placeholder bundle"}',
            )

        buffer.seek(0)
        headers = {
            "Content-Disposition": f'attachment; filename="artifacts_{task_id}.zip"'
        }
        return StreamingResponse(buffer, media_type="application/zip", headers=headers)
    except Exception as e:
        logger.error("Failed to build artifacts bundle", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to build artifacts bundle")
