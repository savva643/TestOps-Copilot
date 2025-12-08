import pytest

from app.services.openapi_parser import OpenAPIParser


@pytest.mark.asyncio
async def test_parse_sample_spec_oneof_allof_anyof():
    spec_yaml = """
openapi: 3.0.1
info:
  title: Sample API
  version: "1.0.0"
paths:
  /items:
    get:
      summary: List items
      parameters:
        - name: q
          in: query
          schema:
            type: string
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                oneOf:
                  - $ref: '#/components/schemas/Item'
                  - type: array
                    items:
                      $ref: '#/components/schemas/Item'
  /items/{id}:
    get:
      summary: Get item
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/Item'
                  - type: object
                    properties:
                      meta:
                        type: object
                        properties:
                          source:
                            type: string
components:
  schemas:
    Item:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        tags:
          type: array
          items:
            anyOf:
              - type: string
              - type: integer
"""
    parser = OpenAPIParser()
    content = spec_yaml.encode("utf-8")
    result = await parser.parse(content, "sample.yaml")
    assert result["endpoints"]
    assert result["schemas"]
    # Ensure oneOf/allOf/anyOf structures preserved
    responses = result["endpoints"][0]["responses"]
    assert any("oneOf" in (resp.get("content", {}).get("application/json", {}).get("schema", {}) or {}) for resp in responses)
    assert any("allOf" in (resp.get("content", {}).get("application/json", {}).get("schema", {}) or {}) for resp in responses)

