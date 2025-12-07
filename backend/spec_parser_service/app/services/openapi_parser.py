"""OpenAPI specification parser."""

import yaml
import json
from typing import Dict, Any, List
import structlog
from prance import ResolvingParser

logger = structlog.get_logger()


class OpenAPIParser:
    """Parser for OpenAPI 3.0 specifications."""

    async def parse(self, content: bytes, filename: str) -> Dict[str, Any]:
        """
        Parse OpenAPI specification content.

        Args:
            content: File content (bytes)
            filename: Original filename

        Returns:
            Structured data with endpoints, schemas, and info
        """
        try:
            # Decode content
            text_content = content.decode("utf-8")

            # Parse YAML or JSON
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                spec_dict = yaml.safe_load(text_content)
            else:
                spec_dict = json.loads(text_content)

            # Resolve references using prance
            parser = ResolvingParser(spec=spec_dict, backend="openapi-spec-validator")
            resolved_spec = parser.specification

            # Extract endpoints
            endpoints = self._extract_endpoints(resolved_spec)

            # Extract schemas
            schemas = resolved_spec.get("components", {}).get("schemas", {})

            # Extract info
            info = resolved_spec.get("info", {})

            result = {
                "endpoints": endpoints,
                "schemas": schemas,
                "info": info,
            }

            logger.info("OpenAPI spec parsed successfully", endpoints_count=len(endpoints))

            return result

        except Exception as e:
            logger.error("Failed to parse OpenAPI spec", error=str(e))
            raise

    def _extract_endpoints(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract endpoints from OpenAPI spec."""
        endpoints = []
        paths = spec.get("paths", {})

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    endpoint = {
                        "path": path,
                        "method": method.upper(),
                        "operation_id": operation.get("operationId"),
                        "summary": operation.get("summary"),
                        "description": operation.get("description"),
                        "parameters": operation.get("parameters", []),
                        "request_body": operation.get("requestBody"),
                        "responses": operation.get("responses", {}),
                        "tags": operation.get("tags", []),
                    }
                    endpoints.append(endpoint)

        return endpoints




