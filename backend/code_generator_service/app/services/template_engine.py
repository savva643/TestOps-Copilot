"""Template engine for code generation."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import subprocess
import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = structlog.get_logger()


class TemplateEngine:
    """Engine for generating code from Jinja2 templates."""

    def __init__(self):
        """Initialize template engine."""
        # Templates are in app/services/templates directory
        template_dir = Path(__file__).parent / "templates"
        # Create directory if it doesn't exist
        template_dir.mkdir(parents=True, exist_ok=True)
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    async def generate(
        self,
        test_case: str,
        test_type: str = "manual",
        feature: Optional[str] = None,
        story: Optional[str] = None,
        priority: str = "NORMAL",
        owner: Optional[str] = None,
        jira_link: Optional[str] = None,
        specification: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate code from template.

        Args:
            test_case: Test case description/steps
            test_type: Type of test (manual, api, ui)
            feature: Feature name
            story: Story name
            priority: Priority (CRITICAL, NORMAL, LOW)
            owner: Test owner
            jira_link: JIRA ticket link
            specification: API specification (for API/UI tests)

        Returns:
            Generated code
        """
        try:
            # Select template based on test type
            template_name = f"{test_type}_test.j2"
            
            # Check if template exists, fallback to manual
            template_path = Path(__file__).parent / "templates" / template_name
            if not template_path.exists():
                template_name = "manual_test.j2"
                test_type = "manual"

            template = self.env.get_template(template_name)

            # Prepare context
            context = {
                "test_case": test_case,
                "test_type": test_type,
                "feature": feature or "Default Feature",
                "story": story or "Default Story",
                "priority": priority,
                "owner": owner or "QA Team",
                "jira_link": jira_link,
                "specification": specification or {},
            }

            # Generate code
            code = template.render(**context)

            logger.info("Code generated successfully", test_type=test_type)

            return code

        except Exception as e:
            logger.error("Failed to generate code", error=str(e))
            raise

    async def format_code(self, code: str) -> str:
        """
        Format Python code using black.

        Args:
            code: Raw Python code

        Returns:
            Formatted code
        """
        try:
            # Use black to format code
            result = subprocess.run(
                ["black", "--code", code, "--line-length", "100"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                return result.stdout
            else:
                # If black fails, return original code
                logger.warning("Black formatting failed, returning original code")
                return code

        except Exception as e:
            logger.warning("Failed to format code with black", error=str(e))
            return code

