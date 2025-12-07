"""Parser endpoints."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import structlog

from app.services.openapi_parser import OpenAPIParser
from app.services.text_parser import TextParser

logger = structlog.get_logger()

router = APIRouter()


class ParseResponse(BaseModel):
    """Response model for parsing."""

    endpoints: List[Dict[str, Any]]
    schemas: Dict[str, Any]
    info: Dict[str, Any]


@router.post("/openapi", response_model=ParseResponse)
async def parse_openapi(file: UploadFile = File(...)):
    """
    Parse OpenAPI 3.0 specification file.
    
    Accepts YAML or JSON OpenAPI specification and returns structured data.
    """
    try:
        content = await file.read()
        parser = OpenAPIParser()
        
        result = await parser.parse(content, file.filename)
        
        return ParseResponse(
            endpoints=result.get("endpoints", []),
            schemas=result.get("schemas", {}),
            info=result.get("info", {}),
        )
    except Exception as e:
        logger.error("Failed to parse OpenAPI spec", error=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to parse OpenAPI: {str(e)}")


@router.post("/text")
async def parse_text(description: str):
    """
    Parse text description into structured format.
    
    Uses LLM or rule-based parsing to extract requirements.
    """
    try:
        parser = TextParser()
        result = await parser.parse(description)
        
        return result
    except Exception as e:
        logger.error("Failed to parse text", error=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to parse text: {str(e)}")




