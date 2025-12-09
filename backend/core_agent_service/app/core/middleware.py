"""Middleware for error handling and logging."""

import time
import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import TestOpsCopilotError
from app.core.metrics import increment_counter, record_request_time

logger = structlog.get_logger()


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle exceptions and return proper error responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except TestOpsCopilotError as e:
            increment_counter("errors_testops", 1)
            logger.error(
                "TestOps Copilot error",
                error=e.message,
                details=e.details,
                path=request.url.path,
                method=request.method,
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": e.message,
                    "details": e.details,
                    "type": e.__class__.__name__,
                },
            )
        except Exception as e:
            increment_counter("errors_unhandled", 1)
            logger.error(
                "Unhandled exception",
                error=str(e),
                path=request.url.path,
                method=request.method,
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred",
                },
            )


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Skip metrics endpoint
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_host=request.client.host if request.client else None,
        )
        
        increment_counter("requests_total", 1)
        
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        duration_ms = round(duration * 1000, 2)
        
        # Record metrics
        record_request_time(request.url.path, duration_ms)
        if response.status_code >= 400:
            increment_counter(f"errors_{response.status_code}", 1)
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        
        return response

