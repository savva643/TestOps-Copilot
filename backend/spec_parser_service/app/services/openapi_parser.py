"""OpenAPI specification parser."""

import yaml
import json
from typing import Dict, Any, List, Union
import structlog
from prance import ResolvingParser
from openapi_spec_validator import validate_spec

from app.core.exceptions import ParsingError, ValidationError, UnsupportedFormatError

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
            try:
                text_content = content.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ParsingError(
                    "Failed to decode file content as UTF-8",
                    details={"filename": filename, "error": str(e)},
                )

            # Parse YAML or JSON
            try:
                if filename.endswith(".yaml") or filename.endswith(".yml"):
                    spec_dict = yaml.safe_load(text_content)
                elif filename.endswith(".json"):
                    spec_dict = json.loads(text_content)
                else:
                    raise UnsupportedFormatError(
                        "Unsupported file format. Expected .yaml, .yml, or .json",
                        details={"filename": filename},
                    )
            except (yaml.YAMLError, json.JSONDecodeError) as e:
                raise ParsingError(
                    "Failed to parse file as YAML or JSON",
                    details={"filename": filename, "error": str(e)},
                )

            # Validate spec (schema-level)
            try:
                validate_spec(spec_dict)
            except Exception as e:
                raise ValidationError(
                    "OpenAPI specification validation failed",
                    details={"filename": filename, "error": str(e)},
                )

            # Resolve references using prance
            try:
                parser = ResolvingParser(spec=spec_dict, backend="openapi-spec-validator")
                resolved_spec = parser.specification
            except Exception as e:
                raise ParsingError(
                    "Failed to resolve OpenAPI references",
                    details={"filename": filename, "error": str(e)},
                )

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

        except (ParsingError, ValidationError, UnsupportedFormatError):
            raise
        except Exception as e:
            logger.error("Unexpected error parsing OpenAPI spec", error=str(e), exc_info=True)
            raise ParsingError(
                "Unexpected error during parsing",
                details={"filename": filename, "error": str(e)},
            )

    def _extract_endpoints(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract endpoints from OpenAPI spec with merged parameters and normalized bodies."""
        endpoints: List[Dict[str, Any]] = []
        paths = spec.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            common_params = path_item.get("parameters", [])
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete", "patch", "options", "head"]:
                    continue
                if not isinstance(operation, dict):
                    continue

                merged_params = self._merge_parameters(common_params, operation.get("parameters", []))
                endpoint = {
                    "path": path,
                    "method": method.upper(),
                    "operation_id": operation.get("operationId"),
                    "summary": operation.get("summary"),
                    "description": operation.get("description"),
                    "parameters": [self._normalize_parameter(p) for p in merged_params],
                    "request_body": self._extract_request_body(operation.get("requestBody")),
                    "responses": self._extract_responses(operation.get("responses", {})),
                    "tags": operation.get("tags", []),
                }
                endpoints.append(endpoint)

        return endpoints

    def _merge_parameters(self, path_params: List[Dict[str, Any]], op_params: List[Dict[str, Any]]):
        """Merge path-level and operation-level parameters (operation overrides)."""
        merged = {(p.get("name"), p.get("in")): p for p in path_params or []}
        for p in op_params or []:
            merged[(p.get("name"), p.get("in"))] = p
        return list(merged.values())

    def _normalize_parameter(self, param: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(param, dict):
            return param
        schema = param.get("schema")
        return {
            **param,
            "schema": self._normalize_schema(schema),
        }

    def _extract_request_body(self, request_body: Dict[str, Any] | None):
        if not request_body:
            return None
        content = request_body.get("content", {})
        return {
            "description": request_body.get("description"),
            "required": request_body.get("required", False),
            "content": {
                ctype: {
                    "schema": self._normalize_schema(media.get("schema")),
                    "examples": media.get("examples") or media.get("example"),
                }
                for ctype, media in content.items()
            },
        }

    def _extract_responses(self, responses: Dict[str, Any]):
        result = []
        for code, resp in responses.items():
            content = resp.get("content", {}) if isinstance(resp, dict) else {}
            result.append(
                {
                    "code": code,
                    "description": resp.get("description") if isinstance(resp, dict) else None,
                    "content": {
                        ctype: {
                            "schema": self._normalize_schema(media.get("schema")),
                            "examples": media.get("examples") or media.get("example"),
                        }
                        for ctype, media in content.items()
                    },
                }
            )
        return result

    def _normalize_schema(self, schema: Union[Dict[str, Any], None]) -> Union[Dict[str, Any], None]:
        """Normalize schemas to preserve oneOf/allOf/anyOf structure."""
        if not schema or not isinstance(schema, dict):
            return schema

        normalized = dict(schema)

        # Recursively normalize composition keywords
        for key in ["oneOf", "allOf", "anyOf"]:
            if key in normalized and isinstance(normalized[key], list):
                normalized[key] = [self._normalize_schema(s) for s in normalized[key]]

        # Normalize items for arrays
        if "items" in normalized:
            normalized["items"] = self._normalize_schema(normalized.get("items"))

        # Normalize properties for objects
        if "properties" in normalized and isinstance(normalized["properties"], dict):
            normalized["properties"] = {
                pname: self._normalize_schema(pschema)
                for pname, pschema in normalized["properties"].items()
            }

        return normalized




