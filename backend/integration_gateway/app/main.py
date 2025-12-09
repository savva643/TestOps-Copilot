"""Main FastAPI application for Integration Gateway."""

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import httpx

from app.core.config import settings
from app.core.security import verify_api_key
from app.core.middleware import ErrorHandlingMiddleware, LoggingMiddleware, RateLimitMiddleware
from app.api.v1.router import api_router

logger = structlog.get_logger()

app = FastAPI(
    title="TestOps Copilot API Gateway",
    description="Single entry point for TestOps Copilot services",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Error handling middleware (should be first)
app.add_middleware(ErrorHandlingMiddleware)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# Logging middleware
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1", dependencies=[Depends(verify_api_key)])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "integration-gateway"}


@app.get("/metrics")
async def get_metrics():
    """Get service metrics."""
    from app.core.metrics import get_metrics
    return get_metrics()


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Integration Gateway starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Integration Gateway shutting down")

