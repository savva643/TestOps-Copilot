"""Custom exceptions for Core Agent Service."""


class TestOpsCopilotError(Exception):
    """Base exception for all TestOps Copilot errors."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class LLMError(TestOpsCopilotError):
    """Exception raised when LLM API call fails."""

    pass


class PromptValidationError(TestOpsCopilotError):
    """Exception raised when prompt validation fails."""

    pass


class TaskError(TestOpsCopilotError):
    """Exception raised when Celery task fails."""

    pass


class ServiceUnavailableError(TestOpsCopilotError):
    """Exception raised when external service is unavailable."""

    pass

