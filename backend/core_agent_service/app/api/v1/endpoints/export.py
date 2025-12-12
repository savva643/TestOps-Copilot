"""Export endpoints for test cases in various formats."""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import yaml
import xml.etree.ElementTree as ET
from xml.dom import minidom
import structlog

from app.core.security import verify_api_key
from app.tasks.celery_app import celery_app
from app.db import get_db
from app.models import TaskRecord
from sqlalchemy.orm import Session

logger = structlog.get_logger()

router = APIRouter()


class ExportRequest(BaseModel):
    """Request model for export."""

    task_id: str
    format: str  # json, yaml, xml, zip


@router.get("/export/{task_id}")
async def export_task(
    task_id: str,
    format: str = Query("json", regex="^(json|yaml|xml|zip)$"),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Export test case in various formats: JSON, YAML, XML, or ZIP.
    
    Formats:
    - json: Structured JSON with metadata
    - yaml: YAML format
    - xml: XML format
    - zip: ZIP archive (same as /artifacts endpoint)
    """
    try:
        # Try to get from database first
        task_record = db.get(TaskRecord, task_id)
        
        # Get task result from Celery
        task_result = celery_app.AsyncResult(task_id)
        
        result = None
        if task_result.ready() and not task_result.failed():
            result = task_result.result
        elif task_record and task_record.result_summary:
            # Fallback to database record
            result = {
                "status": task_record.status,
                "test_type": task_record.test_type,
                "priority": task_record.priority,
                "feature": task_record.feature,
                "story": task_record.story,
                "owner": task_record.owner,
                "jira_link": task_record.jira_link,
                "test_case": {
                    "files": []
                }
            }
        
        if not result:
            raise HTTPException(status_code=404, detail="Task not found or not completed yet")
        
        if task_result.failed():
            raise HTTPException(status_code=500, detail=f"Task failed: {task_result.result}")
        
        # Extract test case data
        test_case_data = result.get("test_case", {})
        if isinstance(test_case_data, str):
            # Old format - single string
            test_case_data = {
                "files": [
                    {
                        "description": None,
                        "code": test_case_data,
                        "filename": "test.py",
                    }
                ]
            }
        
        # Prepare export data
        export_data = {
            "task_id": task_id,
            "status": result.get("status", "unknown"),
            "test_type": result.get("test_type", "unknown"),
            "priority": result.get("priority"),
            "feature": result.get("feature"),
            "story": result.get("story"),
            "owner": result.get("owner"),
            "jira_link": result.get("jira_link"),
            "test_case": test_case_data,
        }
        
        # Export in requested format
        if format == "json":
            content = json.dumps(export_data, indent=2, ensure_ascii=False)
            return Response(
                content=content,
                media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="test_case_{task_id}.json"'},
            )
        
        elif format == "yaml":
            content = yaml.dump(export_data, allow_unicode=True, default_flow_style=False)
            return Response(
                content=content,
                media_type="application/x-yaml",
                headers={"Content-Disposition": f'attachment; filename="test_case_{task_id}.yaml"'},
            )
        
        elif format == "xml":
            # Convert to XML
            root = ET.Element("test_case")
            root.set("task_id", task_id)
            root.set("status", export_data.get("status", "unknown"))
            root.set("test_type", export_data.get("test_type", "unknown"))
            
            if export_data.get("priority"):
                ET.SubElement(root, "priority").text = export_data["priority"]
            if export_data.get("feature"):
                ET.SubElement(root, "feature").text = export_data["feature"]
            if export_data.get("story"):
                ET.SubElement(root, "story").text = export_data["story"]
            if export_data.get("owner"):
                ET.SubElement(root, "owner").text = export_data["owner"]
            if export_data.get("jira_link"):
                ET.SubElement(root, "jira_link").text = export_data["jira_link"]
            
            files_elem = ET.SubElement(root, "files")
            test_case = export_data.get("test_case", {})
            files_list = test_case.get("files", [])
            
            for file_data in files_list:
                file_elem = ET.SubElement(files_elem, "file")
                file_elem.set("filename", file_data.get("filename", "unknown"))
                if file_data.get("description"):
                    ET.SubElement(file_elem, "description").text = file_data["description"]
                ET.SubElement(file_elem, "code").text = file_data.get("code", "")
            
            # Pretty print XML
            xml_str = ET.tostring(root, encoding="unicode")
            dom = minidom.parseString(xml_str)
            content = dom.toprettyxml(indent="  ")
            
            return Response(
                content=content,
                media_type="application/xml",
                headers={"Content-Disposition": f'attachment; filename="test_case_{task_id}.xml"'},
            )
        
        else:  # zip - redirect to artifacts endpoint
            raise HTTPException(status_code=400, detail="Use /artifacts endpoint for ZIP export")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Export failed", task_id=task_id, format=format, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

