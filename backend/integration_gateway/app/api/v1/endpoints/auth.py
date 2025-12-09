"""Auth endpoints for obtaining Cloud.ru IAM tokens via gateway."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter()


class TokenRequest(BaseModel):
    keyId: str
    secret: str


@router.post("/auth/token")
async def get_iam_token(payload: TokenRequest):
    """
    Proxy to Cloud.ru IAM to obtain access token.

    The token is returned as-is from IAM API.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                settings.IAM_AUTH_URL,
                json={"keyId": payload.keyId, "secret": payload.secret},
                headers={"Content-Type": "application/json"},
            )
        resp.raise_for_status()
        data = resp.json()
        logger.info("IAM token issued", has_token=bool(data.get("access_token")))
        return data
    except httpx.HTTPStatusError as e:
        detail = e.response.text
        logger.error("IAM token request failed", status=e.response.status_code, detail=detail)
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except Exception as e:
        logger.error("Unexpected error requesting IAM token", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to obtain IAM token")

