"""Custom exceptions for Spec Parser Service."""


class TestOpsCopilotError(Exception):
    """Base exception for all TestOps Copilot errors."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ParsingError(TestOpsCopilotError):
    """Exception raised when parsing fails."""

    pass


class ValidationError(TestOpsCopilotError):
    """Exception raised when specification validation fails."""

    pass


class UnsupportedFormatError(TestOpsCopilotError):
    """Exception raised when file format is not supported."""

    pass

