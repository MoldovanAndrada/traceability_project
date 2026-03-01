import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_DIR = BASE_DIR / "schemas"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no} invalid JSON: {exc}") from exc
            yield line_no, payload


def _is_type(value: Any, schema_type: str) -> bool:
    type_map = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
    }
    checker = type_map.get(schema_type)
    return checker(value) if checker else True


def _validate_format(value: str, fmt: str) -> bool:
    try:
        if fmt == "date":
            date.fromisoformat(value)
            return True
        if fmt == "date-time":
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
    except ValueError:
        return False
    return True


def _validate_against_schema(payload: Any, schema: dict[str, Any], path: str = "") -> list[str]:
    errors: list[str] = []

    schema_type = schema.get("type")
    if schema_type and not _is_type(payload, schema_type):
        errors.append(f"{path or '$'}: expected {schema_type}")
        return errors

    if "enum" in schema and payload not in schema["enum"]:
        errors.append(f"{path or '$'}: must be one of {schema['enum']}")

    if isinstance(payload, str):
        min_length = schema.get("minLength")
        if min_length is not None and len(payload) < min_length:
            errors.append(f"{path or '$'}: minLength is {min_length}")

        pattern = schema.get("pattern")
        if pattern:
            import re

            if not re.match(pattern, payload):
                errors.append(f"{path or '$'}: does not match pattern {pattern}")

        fmt = schema.get("format")
        if fmt and not _validate_format(payload, fmt):
            errors.append(f"{path or '$'}: invalid {fmt} format")

    if isinstance(payload, (int, float)):
        minimum = schema.get("minimum")
        if minimum is not None and payload < minimum:
            errors.append(f"{path or '$'}: must be >= {minimum}")

    if isinstance(payload, dict):
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in payload:
                errors.append(f"{path or '$'}: missing required field '{field}'")

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in payload.keys():
                if key not in properties:
                    errors.append(f"{path or '$'}: additional property '{key}' is not allowed")

        for key, value in payload.items():
            if key in properties:
                child_path = f"{path}.{key}" if path else key
                errors.extend(_validate_against_schema(value, properties[key], child_path))

    if isinstance(payload, list) and "items" in schema:
        for idx, item in enumerate(payload):
            child_path = f"{path}[{idx}]" if path else f"[{idx}]"
            errors.extend(_validate_against_schema(item, schema["items"], child_path))

    return errors


def validate_jsonl(data_path: Path, schema_path: Path) -> list[str]:
    schema = _load_json(schema_path)

    errors: list[str] = []
    for line_no, payload in _iter_jsonl(data_path):
        for err in _validate_against_schema(payload, schema):
            errors.append(f"{data_path}:{line_no}: {err}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate canonical traceability JSONL files against JSON Schemas."
    )
    parser.add_argument("--artifacts", type=Path, help="Path to artifacts.jsonl")
    parser.add_argument("--edges", type=Path, help="Path to edges.jsonl")
    parser.add_argument(
        "--artifact-schema",
        type=Path,
        default=SCHEMA_DIR / "artifacts.schema.json",
        help="Path to artifacts schema JSON",
    )
    parser.add_argument(
        "--edge-schema",
        type=Path,
        default=SCHEMA_DIR / "edges.schema.json",
        help="Path to edges schema JSON",
    )
    args = parser.parse_args()

    if not args.artifacts and not args.edges:
        parser.error("Provide at least one of --artifacts or --edges")

    all_errors: list[str] = []
    if args.artifacts:
        all_errors.extend(validate_jsonl(args.artifacts, args.artifact_schema))
    if args.edges:
        all_errors.extend(validate_jsonl(args.edges, args.edge_schema))

    if all_errors:
        print("Validation failed:")
        for err in all_errors:
            print(f" - {err}")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
