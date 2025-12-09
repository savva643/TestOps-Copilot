"""Main FastAPI application for Spec Parser Service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.core.middleware import ErrorHandlingMiddleware, LoggingMiddleware
from app.api.v1.router import api_router

logger = structlog.get_logger()

app = FastAPI(
    title="Spec Parser Service",
    description="Parses specifications (OpenAPI, text) into structured format",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Error handling middleware (should be first)
app.add_middleware(ErrorHandlingMiddleware)

# Logging middleware
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "spec-parser-service"}


@app.get("/metrics")
async def get_metrics():
    """Get service metrics."""
    from app.core.metrics import get_metrics
    return get_metrics()


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Spec Parser Service starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Spec Parser Service shutting down")




