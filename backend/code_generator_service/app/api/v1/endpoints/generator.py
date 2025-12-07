"""Code generator endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import structlog

from app.services.template_engine import TemplateEngine

logger = structlog.get_logger()

router = APIRouter()


class GenerateCodeRequest(BaseModel):
    """Request model for code generation."""

    test_case: str
    test_type: str = "manual"  # manual, api, ui
    feature: Optional[str] = None
    story: Optional[str] = None
    priority: str = "NORMAL"
    owner: Optional[str] = None
    jira_link: Optional[str] = None
    specification: Optional[Dict[str, Any]] = None


class GenerateCodeResponse(BaseModel):
    """Response model for code generation."""

    code: str
    formatted_code: str
    test_type: str


@router.post("/code", response_model=GenerateCodeResponse)
async def generate_code(request: GenerateCodeRequest):
    """
    Generate test code from test case and specification.
    
    Uses Jinja2 templates to format the code according to Allure TestOps as Code format.
    """
    try:
        template_engine = TemplateEngine()
        
        code = await template_engine.generate(
            test_case=request.test_case,
            test_type=request.test_type,
            feature=request.feature,
            story=request.story,
            priority=request.priority,
            owner=request.owner,
            jira_link=request.jira_link,
            specification=request.specification,
        )
        
        # Format code with black
        formatted_code = await template_engine.format_code(code)
        
        return GenerateCodeResponse(
            code=code,
            formatted_code=formatted_code,
            test_type=request.test_type,
        )
    except Exception as e:
        logger.error("Failed to generate code", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

