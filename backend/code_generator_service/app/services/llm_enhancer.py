"""Lightweight hook to enhance generated code via LLM (stub/placeholder)."""

from typing import Dict, Any


class LLMEnhancer:
    """
    Stub implementation: here you can integrate a real LLM to improve code.
    Currently, it appends a short comment for traceability.
    """

    async def enhance(self, code: str, context: Dict[str, Any] | None = None) -> str:
        suffix = "\n# Enhanced by LLM placeholder\n"
        if code.endswith(suffix):
            return code
        return code + suffix

