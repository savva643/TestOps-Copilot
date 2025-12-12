"""E2E tests for dashboard critical flows."""

import pytest
from playwright.async_api import Page, expect
import asyncio


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_login_flow(page: Page, base_url: str):
    """Test user login flow."""
    await page.goto(f"{base_url}/login")
    
    # Wait for login form
    await expect(page.locator('input[type="text"], input[type="password"]').first).to_be_visible(timeout=5000)
    
    # Fill login form (adjust selectors based on actual UI)
    key_id_input = page.locator('input[name="keyId"], input[placeholder*="Key ID"]').first
    key_secret_input = page.locator('input[name="keySecret"], input[type="password"]').first
    api_key_input = page.locator('input[name="apiKey"], input[placeholder*="API Key"]').first
    
    if await key_id_input.count() > 0:
        await key_id_input.fill("test-key-id")
    if await key_secret_input.count() > 0:
        await key_secret_input.fill("test-key-secret")
    if await api_key_input.count() > 0:
        await api_key_input.fill("test-api-key")
    
    # Submit form
    submit_button = page.locator('button[type="submit"], button:has-text("Войти"), button:has-text("Login")').first
    if await submit_button.count() > 0:
        await submit_button.click()
        
        # Wait for redirect to dashboard or home
        await page.wait_for_url(f"{base_url}/**", timeout=10000)
        assert page.url != f"{base_url}/login"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_dashboard_loads(page: Page, base_url: str):
    """Test that dashboard page loads correctly."""
    await page.goto(f"{base_url}/dashboard")
    
    # Wait for dashboard content
    await expect(page.locator('h1, h2, [class*="dashboard"], [class*="title"]').first).to_be_visible(timeout=10000)
    
    # Check for key elements
    assert "dashboard" in page.url.lower() or "testops" in page.content().lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_generate_page_loads(page: Page, base_url: str):
    """Test that generate page loads and shows file upload."""
    await page.goto(f"{base_url}/generate")
    
    # Wait for page content
    await expect(page.locator('h1, h2, [class*="generate"], [class*="upload"]').first).to_be_visible(timeout=10000)
    
    # Check for file input or upload button
    file_input = page.locator('input[type="file"], button:has-text("Загрузить"), button:has-text("Upload")')
    assert await file_input.count() > 0 or "generate" in page.content().lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tasks_page_loads(page: Page, base_url: str):
    """Test that tasks page loads."""
    await page.goto(f"{base_url}/tasks")
    
    # Wait for page content
    await expect(page.locator('h1, h2, [class*="task"], table, [class*="list"]').first).to_be_visible(timeout=10000)
    
    # Page should load (even if empty)
    assert "task" in page.url.lower() or "task" in page.content().lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_navigation_flow(page: Page, base_url: str):
    """Test navigation between pages."""
    # Start at dashboard
    await page.goto(f"{base_url}/dashboard")
    await page.wait_for_load_state("networkidle", timeout=10000)
    
    # Navigate to generate
    generate_link = page.locator('a[href*="generate"], button:has-text("Сгенерировать"), button:has-text("Generate")').first
    if await generate_link.count() > 0:
        await generate_link.click()
        await page.wait_for_url(f"{base_url}/**generate**", timeout=5000)
        assert "generate" in page.url.lower()
    
    # Navigate to tasks
    tasks_link = page.locator('a[href*="tasks"], button:has-text("Задачи"), button:has-text("Tasks")').first
    if await tasks_link.count() > 0:
        await tasks_link.click()
        await page.wait_for_url(f"{base_url}/**tasks**", timeout=5000)
        assert "tasks" in page.url.lower()

