"""Pytest configuration for E2E tests."""

import pytest
from playwright.async_api import async_playwright, Browser, Page, BrowserContext


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance for E2E tests."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: Browser) -> Page:
    """Create a new page for each test."""
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await context.close()


@pytest.fixture
def base_url():
    """Base URL for frontend."""
    return "http://localhost:3000"


@pytest.fixture
def api_url():
    """API Gateway URL."""
    return "http://localhost:8000"

