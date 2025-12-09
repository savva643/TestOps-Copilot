"""Custom exceptions for Code Generator Service."""


class TestOpsCopilotError(Exception):
    """Base exception for all TestOps Copilot errors."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class TemplateError(TestOpsCopilotError):
    """Exception raised when template rendering fails."""

    pass


class CodeValidationError(TestOpsCopilotError):
    """Exception raised when generated code validation fails."""

    pass


class FormattingError(TestOpsCopilotError):
    """Exception raised when code formatting fails."""

    pass

