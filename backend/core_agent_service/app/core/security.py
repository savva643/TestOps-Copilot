"""Security utilities."""

from typing import Optional
from fastapi import Header, HTTPException, status


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key from header."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
        )
    # TODO: Implement proper API key validation
    return x_api_key




