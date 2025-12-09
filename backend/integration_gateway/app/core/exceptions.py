"""Custom exceptions for Integration Gateway."""


class TestOpsCopilotError(Exception):
    """Base exception for all TestOps Copilot errors."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ProxyError(TestOpsCopilotError):
    """Exception raised when proxying request fails."""

    pass


class ServiceUnavailableError(TestOpsCopilotError):
    """Exception raised when backend service is unavailable."""

    pass

