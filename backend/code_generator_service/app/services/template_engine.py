"""Template engine for code generation."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import subprocess
import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound, TemplateError

from app.core.exceptions import TemplateError, FormattingError

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
        strict: bool = False,
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

            # Map optional aliases to existing templates
            aliases = {
                "contract": "contract_test.j2",
                "api": "api_test.j2",
                "ui": "ui_test.j2",
                "manual": "manual_test.j2",
            }
            template_name = aliases.get(test_type, template_name)

            # Strict variants (Приложение 1)
            if strict:
                strict_aliases = {
                    "manual": "manual_test_strict.j2",
                    "api": "api_test_strict.j2",
                    "ui": "ui_test_strict.j2",
                }
                template_name = strict_aliases.get(test_type, template_name)

            # Check if template exists, fallback to manual
            template_path = Path(__file__).parent / "templates" / template_name
            if not template_path.exists():
                template_name = "manual_test.j2"
                test_type = "manual"

            try:
                template = self.env.get_template(template_name)
            except TemplateNotFound as e:
                raise TemplateError(
                    f"Template not found: {template_name}",
                    details={"template_name": template_name, "test_type": test_type},
                )

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
            try:
                code = template.render(**context)
            except TemplateError as e:
                raise TemplateError(
                    "Failed to render template",
                    details={"template_name": template_name, "error": str(e)},
                )

            logger.info("Code generated successfully", test_type=test_type)

            return code

        except TemplateError:
            raise
        except Exception as e:
            logger.error("Unexpected error generating code", error=str(e), exc_info=True)
            raise TemplateError(
                "Unexpected error during code generation",
                details={"test_type": test_type, "error": str(e)},
            )

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
                # If black fails, log warning but return original code (non-critical)
                logger.warning(
                    "Black formatting failed, returning original code",
                    error=result.stderr,
                )
                return code

        except FileNotFoundError:
            logger.warning("Black formatter not found, returning original code")
            return code
        except Exception as e:
            logger.warning("Failed to format code with black", error=str(e))
            return code

