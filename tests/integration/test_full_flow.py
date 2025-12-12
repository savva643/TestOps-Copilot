"""Integration tests for full flow: parse -> generate -> download."""

import pytest
import httpx
import asyncio
from pathlib import Path

# Base URLs (adjust if needed)
GATEWAY_URL = "http://localhost:8000"
API_KEY = "testops-copilot-api-key-2024"

# Sample OpenAPI spec for testing
SAMPLE_SPEC = """
openapi: 3.0.1
info:
  title: Test API
  version: "1.0.0"
paths:
  /api/v1/test:
    get:
      summary: Get test data
      responses:
        "200":
          description: Success
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: integer
                  name:
                    type: string
"""


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_flow_parse_generate_download():
    """Test complete flow: parse spec -> generate tests -> check task -> download artifact."""
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Step 1: Parse OpenAPI specification
        files = {
            "file": ("test-api.yaml", SAMPLE_SPEC.encode("utf-8"), "application/yaml")
        }
        
        parse_response = await client.post(
            f"{GATEWAY_URL}/api/v1/parse/openapi",
            files=files,
            headers=headers,
        )
        
        assert parse_response.status_code == 200
        parsed_data = parse_response.json()
        assert "endpoints" in parsed_data
        assert len(parsed_data["endpoints"]) > 0
        
        # Step 2: Generate test case
        generate_response = await client.post(
            f"{GATEWAY_URL}/api/v1/generate/test-case",
            json={
                "description": "Test API endpoint /api/v1/test",
                "test_type": "api",
                "feature": "Test Feature",
                "story": "Test Story",
                "priority": "NORMAL",
                "owner": "QA Team",
            },
            headers=headers,
        )
        
        assert generate_response.status_code in [200, 201, 202]
        task_data = generate_response.json()
        assert "task_id" in task_data
        task_id = task_data["task_id"]
        
        # Step 3: Poll task status until completion (with timeout)
        max_attempts = 60
        attempt = 0
        task_status = None
        
        while attempt < max_attempts:
            status_response = await client.get(
                f"{GATEWAY_URL}/api/v1/tasks/{task_id}",
                headers=headers,
            )
            
            assert status_response.status_code == 200
            task_status = status_response.json()
            status = task_status.get("status", "").upper()
            
            if status in ["SUCCESS", "COMPLETED", "FAILED", "FAILURE"]:
                break
            
            await asyncio.sleep(2)
            attempt += 1
        
        # Step 4: Verify task completed successfully
        assert task_status is not None
        final_status = task_status.get("status", "").upper()
        
        # If failed, log error for debugging
        if final_status in ["FAILED", "FAILURE"]:
            error_msg = task_status.get("error", "Unknown error")
            pytest.fail(f"Task failed: {error_msg}")
        
        assert final_status in ["SUCCESS", "COMPLETED"]
        
        # Step 5: Check for artifact download endpoint
        # Note: Actual download endpoint may vary based on implementation
        if "artifact_url" in task_status or "download_url" in task_status:
            download_url = task_status.get("artifact_url") or task_status.get("download_url")
            download_response = await client.get(
                download_url,
                headers=headers,
                follow_redirects=True,
            )
            assert download_response.status_code == 200
            assert len(download_response.content) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_parse_specification_endpoint():
    """Test OpenAPI parsing endpoint."""
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        files = {
            "file": ("test.yaml", SAMPLE_SPEC.encode("utf-8"), "application/yaml")
        }
        
        response = await client.post(
            f"{GATEWAY_URL}/api/v1/parse/openapi",
            files=files,
            headers=headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert "schemas" in data
        assert "info" in data
        assert len(data["endpoints"]) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_generate_test_case_endpoint():
    """Test test case generation endpoint."""
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{GATEWAY_URL}/api/v1/generate/test-case",
            json={
                "description": "Test user registration flow",
                "test_type": "manual",
                "feature": "User Management",
                "story": "Registration",
                "priority": "NORMAL",
            },
            headers=headers,
        )
        
        assert response.status_code in [200, 201, 202]
        data = response.json()
        assert "task_id" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_task_status_endpoint():
    """Test task status retrieval endpoint."""
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # First create a task
        create_response = await client.post(
            f"{GATEWAY_URL}/api/v1/generate/test-case",
            json={
                "description": "Test task status",
                "test_type": "manual",
            },
            headers=headers,
        )
        
        assert create_response.status_code in [200, 201, 202]
        task_id = create_response.json()["task_id"]
        
        # Then check status
        status_response = await client.get(
            f"{GATEWAY_URL}/api/v1/tasks/{task_id}",
            headers=headers,
        )
        
        assert status_response.status_code == 200
        data = status_response.json()
        assert "task_id" in data
        assert "status" in data
        assert data["task_id"] == task_id

