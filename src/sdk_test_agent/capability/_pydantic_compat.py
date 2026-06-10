from __future__ import annotations

import copy
import types
from enum import Enum
from dataclasses import MISSING, dataclass, field as dc_field, fields, is_dataclass
from typing import Any, ClassVar, get_args, get_origin, get_type_hints

try:  # pragma: no cover - exercised only when the real dependency is installed.
    from pydantic import BaseModel, ConfigDict, Field, ValidationError  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback is covered through capability tests.
    class ValidationError(ValueError):
        def __init__(self, errors: list[str]) -> None:
            self.errors = errors
            super().__init__("; ".join(errors))

    def ConfigDict(**kwargs: Any) -> dict[str, Any]:
        return dict(kwargs)

    def Field(default: Any = MISSING, *, default_factory=None, **metadata: Any):
        if default is MISSING and default_factory is None:
            return dc_field(metadata=metadata)
        if default_factory is not None:
            return dc_field(default_factory=default_factory, metadata=metadata)
        return dc_field(default=default, metadata=metadata)

    class _BaseModelInitSubclass:
        def __init_subclass__(cls, **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)
            if cls.__name__ != "BaseModel":
                dataclass(cls)

    class BaseModel(_BaseModelInitSubclass):
        model_config: ClassVar[dict[str, Any]] = {}

        def __post_init__(self) -> None:
            hints = get_type_hints(self.__class__)
            errors: list[str] = []
            for f in fields(self):
                if f.name == "model_config":
                    continue
                try:
                    setattr(self, f.name, _coerce_value(getattr(self, f.name), hints.get(f.name, Any), f.name))
                except ValidationError as exc:
                    errors.extend(exc.errors)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{f.name}: {exc}")
            if errors:
                raise ValidationError(errors)

        @classmethod
        def model_validate(cls, payload: Any):
            if isinstance(payload, cls):
                return payload
            if not isinstance(payload, dict):
                raise ValidationError([f"expected object for {cls.__name__}"])
            hints = get_type_hints(cls)
            allowed = {f.name for f in fields(cls) if f.name != "model_config"}
            extra = getattr(cls, "model_config", {}).get("extra")
            if extra == "forbid":
                unknown = sorted(set(payload) - allowed)
                if unknown:
                    raise ValidationError([f"extra fields are not permitted: {', '.join(unknown)}"])
            kwargs = {k: v for k, v in payload.items() if k in allowed}
            missing = []
            for f in fields(cls):
                if f.name == "model_config":
                    continue
                if f.name not in kwargs and f.default is MISSING and f.default_factory is MISSING:
                    missing.append(f.name)
            if missing:
                raise ValidationError([f"missing required field: {name}" for name in missing])
            obj = cls(**kwargs)
            for name, value in payload.items():
                if name not in allowed and extra == "allow":
                    setattr(obj, name, value)
            return obj

        def model_dump(self, mode: str = "python", **kwargs: Any) -> dict[str, Any]:
            return _dump_value(self)

        @classmethod
        def model_json_schema(cls) -> dict[str, Any]:
            required: list[str] = []
            properties: dict[str, Any] = {}
            hints = get_type_hints(cls)
            for f in fields(cls):
                if f.name == "model_config":
                    continue
                properties[f.name] = _schema_for_type(hints.get(f.name, Any), dict(f.metadata))
                if f.default is MISSING and f.default_factory is MISSING:
                    required.append(f.name)
            schema: dict[str, Any] = {"title": cls.__name__, "type": "object", "properties": properties}
            if required:
                schema["required"] = required
            extra = getattr(cls, "model_config", {}).get("extra")
            if extra == "forbid":
                schema["additionalProperties"] = False
            elif extra == "allow":
                schema["additionalProperties"] = True
            return schema

    def _dump_value(value: Any) -> Any:
        if is_dataclass(value):
            return {f.name: _dump_value(getattr(value, f.name)) for f in fields(value) if f.name != "model_config"}
        if isinstance(value, dict):
            return {str(k): _dump_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_dump_value(v) for v in value]
        if isinstance(value, Enum):
            return value.value
        return value

    def _is_union(origin: Any) -> bool:
        return origin is types.UnionType or str(origin) == "typing.Union"

    def _coerce_value(value: Any, annotation: Any, path: str) -> Any:
        origin = get_origin(annotation)
        args = get_args(annotation)
        if annotation is Any or annotation is None:
            return value
        if _is_union(origin):
            errors: list[str] = []
            for arg in args:
                if arg is type(None) and value is None:
                    return None
                try:
                    return _coerce_value(value, arg, path)
                except Exception as exc:  # noqa: BLE001
                    errors.append(str(exc))
            raise ValidationError([f"{path}: does not match any allowed type ({'; '.join(errors)})"])
        if origin is list:
            if not isinstance(value, list):
                raise ValidationError([f"{path}: expected list"])
            if args:
                return [_coerce_value(v, args[0], f"{path}[]") for v in value]
            return value
        if origin is tuple:
            if not isinstance(value, (list, tuple)):
                raise ValidationError([f"{path}: expected tuple"])
            inner = args[0] if args and args[-1] is Ellipsis else (args[0] if args else Any)
            return tuple(_coerce_value(v, inner, f"{path}[]") for v in value)
        if origin is dict:
            if not isinstance(value, dict):
                raise ValidationError([f"{path}: expected object"])
            return value
        if str(origin) == "typing.Literal":
            if value not in args:
                raise ValidationError([f"{path}: expected one of {args}"])
            return value
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return annotation.model_validate(value)
        if isinstance(annotation, type) and hasattr(annotation, "__members__"):
            if isinstance(value, annotation):
                return value
            try:
                return annotation(value)
            except Exception as exc:  # noqa: BLE001
                raise ValidationError([f"{path}: invalid enum value {value}"]) from exc
        if annotation in (str, int, bool, float):
            if not isinstance(value, annotation):
                raise ValidationError([f"{path}: expected {annotation.__name__}"])
        return value

    def _schema_for_type(annotation: Any, metadata: dict[str, Any]) -> dict[str, Any]:
        origin = get_origin(annotation)
        args = get_args(annotation)
        schema: dict[str, Any]
        if annotation is Any:
            schema = {}
        elif _is_union(origin):
            schema = {"anyOf": [_schema_for_type(a, {}) if a is not type(None) else {"type": "null"} for a in args]}
        elif origin is list:
            schema = {"type": "array", "items": _schema_for_type(args[0], {}) if args else {}}
        elif origin is tuple:
            schema = {"type": "array", "items": _schema_for_type(args[0], {}) if args else {}}
        elif origin is dict:
            schema = {"type": "object"}
        elif str(origin) == "typing.Literal":
            schema = {"enum": list(args)}
            if args:
                schema["type"] = _json_type(type(args[0]))
        elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
            schema = annotation.model_json_schema()
        elif isinstance(annotation, type) and hasattr(annotation, "__members__"):
            schema = {"type": "string", "enum": [m.value for m in annotation]}
        elif annotation in (str, int, bool, float):
            schema = {"type": _json_type(annotation)}
        else:
            schema = {}
        if "min_length" in metadata:
            schema["minItems"] = metadata["min_length"]
        for src, dst in (("ge", "minimum"), ("le", "maximum")):
            if src in metadata:
                schema[dst] = metadata[src]
        return schema

    def _json_type(tp: type) -> str:
        return {str: "string", int: "integer", bool: "boolean", float: "number"}.get(tp, "object")
