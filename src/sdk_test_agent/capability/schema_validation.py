from __future__ import annotations

from typing import Any


def validate_payload_against_schema(payload: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Return JSON-schema-like validation errors. Empty means valid.

    MVP intentionally implements the subset emitted by capability IO models so the
    project does not need a heavy jsonschema dependency yet.
    """
    return _validate(payload, schema, "$", root_schema=schema)


def _validate(value: Any, schema: dict[str, Any], path: str, *, root_schema: dict[str, Any]) -> list[str]:
    if not schema:
        return []
    if "$ref" in schema:
        schema = _resolve_ref(schema["$ref"], root_schema)
    if "anyOf" in schema:
        branch_errors = [_validate(value, branch, path, root_schema=root_schema) for branch in schema["anyOf"]]
        if any(not errors for errors in branch_errors):
            return []
        return [f"{path}: does not match any allowed schema"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path}: expected one of {schema['enum']}"]

    expected_type = schema.get("type")
    if expected_type == "null":
        return [] if value is None else [f"{path}: expected null"]
    if expected_type == "object":
        if not isinstance(value, dict):
            return [f"{path}: expected object"]
        errors: list[str] = []
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key}: missing required property")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in sorted(set(value) - set(properties)):
                errors.append(f"{path}.{key}: additional property is not allowed")
        for key, sub_value in value.items():
            if key in properties:
                errors.extend(_validate(sub_value, properties[key], f"{path}.{key}", root_schema=root_schema))
        return errors
    if expected_type == "array":
        if not isinstance(value, list):
            return [f"{path}: expected array"]
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            return [f"{path}: expected at least {min_items} item(s)"]
        errors: list[str] = []
        item_schema = schema.get("items", {})
        for idx, item in enumerate(value):
            errors.extend(_validate(item, item_schema, f"{path}[{idx}]", root_schema=root_schema))
        return errors
    if expected_type == "string" and not isinstance(value, str):
        return [f"{path}: expected string"]
    if expected_type == "integer" and not isinstance(value, int):
        return [f"{path}: expected integer"]
    if expected_type == "number" and not isinstance(value, (int, float)):
        return [f"{path}: expected number"]
    if expected_type == "boolean" and not isinstance(value, bool):
        return [f"{path}: expected boolean"]
    if isinstance(value, (int, float)):
        if "minimum" in schema and value < schema["minimum"]:
            return [f"{path}: below minimum {schema['minimum']}"]
        if "maximum" in schema and value > schema["maximum"]:
            return [f"{path}: above maximum {schema['maximum']}"]
    return []


def _resolve_ref(ref: str, root_schema: dict[str, Any]) -> dict[str, Any]:
    prefix = "#/$defs/"
    if ref.startswith(prefix):
        return root_schema.get("$defs", {}).get(ref[len(prefix) :], {})
    return {}
