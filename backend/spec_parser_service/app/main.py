"""Main FastAPI application for Spec Parser Service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.api.v1.router import api_router

logger = structlog.get_logger()

app = FastAPI(
    title="Spec Parser Service",
    description="Parses specifications (OpenAPI, text) into structured format",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

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


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Spec Parser Service starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Spec Parser Service shutting down")




