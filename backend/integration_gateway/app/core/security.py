"""Security utilities."""

from typing import Optional
from fastapi import Header, HTTPException, Query, status
from app.core.config import settings


async def verify_api_key(
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None),
) -> str:
    """
    Verify API key from header or query param.

    WebSocket handshakes can't easily set custom headers in browsers, so we
    also accept the ?api_key= query param to keep WS connections working while
    preserving header-based checks for HTTP calls.
    """
    key = x_api_key or api_key

    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
        )
    
    if key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return key

