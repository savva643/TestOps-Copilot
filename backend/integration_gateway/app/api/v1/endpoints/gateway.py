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
            # Первый запрос - получаем актуальный статус
            first_request = True
            while True:
                try:
                    resp = await client.get(
                        f"{settings.CORE_AGENT_URL}/api/v1/tasks/{task_id}",
                        headers={"X-API-Key": settings.API_KEY},
                        timeout=10.0,
                    )
                    
                    data = resp.json()
                    status = data.get("status", "").upper()
                    
                    # Если это первый запрос и задача уже завершена, отправляем статус и закрываем соединение
                    if first_request and status not in ["PENDING", "PROGRESS", "IN_PROGRESS"]:
                        await websocket.send_text(resp.text)
                        logger.info("Task already completed on first WS request", task_id=task_id, status=status)
                        break
                    
                    # Отправляем обновление только если задача еще активна
                    if status in ["PENDING", "PROGRESS", "IN_PROGRESS"]:
                        await websocket.send_text(resp.text)
                    else:
                        # Задача завершилась во время работы WebSocket
                        await websocket.send_text(resp.text)
                        logger.info("Task completed during WS connection", task_id=task_id, status=status)
                        break

                    first_request = False
                    await asyncio.sleep(1.0)
                except httpx.ConnectError as e:
                    logger.error("Connection error in Task WS", task_id=task_id, error=str(e))
                    await websocket.send_text('{"error":"Backend service unavailable","status":"error"}')
                    break
                except httpx.TimeoutException as e:
                    logger.error("Timeout in Task WS", task_id=task_id, error=str(e))
                    await websocket.send_text('{"error":"Backend service timeout","status":"error"}')
                    break
                except httpx.HTTPStatusError as e:
                    logger.error("HTTP error in Task WS", task_id=task_id, status_code=e.response.status_code, error=str(e))
                    await websocket.send_text(f'{{"error":"Backend service error: {e.response.status_code}","status":"error"}}')
                    break
    except WebSocketDisconnect:
        logger.info("Task WS disconnected", task_id=task_id)
    except Exception as e:
        logger.error("Task WS error", task_id=task_id, error=str(e), exc_info=True)
        try:
            await websocket.send_text('{"error":"websocket_error","status":"error"}')
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
    """Proxy to test-optimizer-service coverage analysis."""
    try:
        body = await request.body()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.TEST_OPTIMIZER_URL}/api/v1/coverage",
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


@router.post("/optimize/duplicates")
async def optimize_duplicates_proxy(request: Request):
    """Proxy to test-optimizer-service duplicate finding."""
    try:
        body = await request.body()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.TEST_OPTIMIZER_URL}/api/v1/duplicates",
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


@router.post("/optimize/recommendations")
async def optimize_recommendations_proxy(request: Request):
    """Proxy to test-optimizer-service optimization recommendations."""
    try:
        body = await request.body()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.TEST_OPTIMIZER_URL}/api/v1/optimize",
                content=body,
                headers=dict(request.headers),
                timeout=90.0,
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


@router.post("/gitlab/generate-and-commit")
async def gitlab_generate_and_commit_proxy(request: Request):
    """Proxy to gitlab-integration-service for generating and committing tests."""
    try:
        body = await request.body()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.GITLAB_INTEGRATION_URL}/api/v1/gitlab/generate-and-commit",
                content=body,
                headers=dict(request.headers),
                timeout=300.0,  # 5 minutes for full workflow
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
            details={"service": "gitlab-integration-service", "error": str(e)},
        )
    except httpx.ConnectError as e:
        logger.error("Connection error proxying request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service unavailable",
            details={"service": "gitlab-integration-service", "error": str(e)},
        )
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error proxying request", status_code=e.response.status_code, error=str(e))
        raise ProxyError(
            f"Backend service returned error: {e.response.status_code}",
            details={"service": "gitlab-integration-service", "status_code": e.response.status_code},
        )
    except Exception as e:
        logger.error("Unexpected error proxying request", error=str(e), exc_info=True)
        raise ProxyError(
            "Failed to proxy request",
            details={"service": "gitlab-integration-service", "error": str(e)},
        )


@router.post("/gitlab/validate-token")
async def gitlab_validate_token_proxy(request: Request):
    """Proxy to gitlab-integration-service for token validation."""
    try:
        body = await request.body()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.GITLAB_INTEGRATION_URL}/api/v1/gitlab/validate",
                content=body,
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
            details={"service": "gitlab-integration-service", "error": str(e)},
        )
    except httpx.ConnectError as e:
        logger.error("Connection error proxying request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service unavailable",
            details={"service": "gitlab-integration-service", "error": str(e)},
        )
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error proxying request", status_code=e.response.status_code, error=str(e))
        raise ProxyError(
            f"Backend service returned error: {e.response.status_code}",
            details={"service": "gitlab-integration-service", "status_code": e.response.status_code},
        )
    except Exception as e:
        logger.error("Unexpected error proxying request", error=str(e), exc_info=True)
        raise ProxyError(
            "Failed to proxy request",
            details={"service": "gitlab-integration-service", "error": str(e)},
        )


@router.get("/gitlab/project/{project_path:path}/tree")
async def gitlab_project_tree_proxy(
    project_path: str,
    request: Request,
):
    """Proxy to gitlab-integration-service for repository tree.

    Используется аналитикой для валидации репозитория и проверки структуры.
    """
    try:
        # Извлекаем токен и базовый URL GitLab из заголовков, как на фронте
        gitlab_token = request.headers.get("X-GitLab-Token")
        gitlab_url = request.headers.get("X-GitLab-URL")

        if not gitlab_token:
          raise HTTPException(status_code=401, detail="GitLab token required")

        params = dict(request.query_params)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.GITLAB_INTEGRATION_URL}/api/v1/gitlab/project/{project_path}/tree",
                params={
                    **params,
                    "private_token": gitlab_token,
                    "gitlab_base_url": gitlab_url or settings.GITLAB_URL,
                },
                timeout=30.0,
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except httpx.TimeoutException as e:
        logger.error("Timeout proxying gitlab project tree request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service timeout",
            details={"service": "gitlab-integration-service", "error": str(e)},
        )
    except httpx.ConnectError as e:
        logger.error("Connection error proxying gitlab project tree request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service unavailable",
            details={"service": "gitlab-integration-service", "error": str(e)},
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error proxying gitlab project tree request",
            status_code=e.response.status_code,
            error=str(e),
        )
        raise ProxyError(
            f"Backend service returned error: {e.response.status_code}",
            details={"service": "gitlab-integration-service", "status_code": e.response.status_code},
        )
    except Exception as e:
        logger.error("Unexpected error proxying gitlab project tree request", error=str(e), exc_info=True)
        raise ProxyError(
            "Failed to proxy request",
            details={"service": "gitlab-integration-service", "error": str(e)},
        )


@router.post("/gitlab/task")
async def gitlab_task_proxy(request: Request):
    """Proxy to core-agent-service for saving GitLab tasks."""
    try:
        body = await request.body()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.CORE_AGENT_URL}/api/v1/gitlab/task",
                content=body,
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


@router.get("/export/{task_id}")
async def export_task_proxy(task_id: str, format: str = "json"):
    """Proxy to core-agent-service for exporting tasks in various formats."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.CORE_AGENT_URL}/api/v1/export/{task_id}",
                params={"format": format},
                headers={"X-API-Key": settings.API_KEY},
                timeout=30.0,
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except httpx.TimeoutException as e:
        logger.error("Timeout proxying export request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service timeout",
            details={"service": "core-agent-service", "error": str(e)},
        )
    except httpx.ConnectError as e:
        logger.error("Connection error proxying export request", error=str(e))
        raise ServiceUnavailableError(
            "Backend service unavailable",
            details={"service": "core-agent-service", "error": str(e)},
        )
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error proxying export request", status_code=e.response.status_code, error=str(e))
        raise ProxyError(
            f"Backend service returned error: {e.response.status_code}",
            details={"service": "core-agent-service", "status_code": e.response.status_code},
        )
    except Exception as e:
        logger.error("Unexpected error proxying export request", error=str(e), exc_info=True)
        raise ProxyError(
            "Failed to proxy export request",
            details={"service": "core-agent-service", "error": str(e)},
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
