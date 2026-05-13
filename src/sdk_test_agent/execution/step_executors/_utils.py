from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from sdk_test_agent.execution.execution_context import ExecutionContext


def jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    return value


def get_input_or_variable(inputs: dict[str, Any], context: ExecutionContext, key: str, default: Any = None) -> Any:
    if key in inputs:
        return inputs[key]
    return context.variables.get(key, default)


def find_output(context: ExecutionContext, key: str, default: Any = None) -> Any:
    for outputs in reversed(list(context.step_outputs.values())):
        if key in outputs:
            return outputs[key]
    return default


def persist_text(context: ExecutionContext, *, kind: str, name: str, text: str, mime_type: str = "text/plain") -> str | None:
    manager = context.artifact_manager
    if manager is None:
        return None
    record = manager.persist_artifact_bytes(
        task_id=context.task_id,
        stage_id=None,
        kind=kind,
        name=name,
        content=text.encode("utf-8"),
        subdir="outputs",
        mime_type=mime_type,
        created_by_action="execution",
    )
    ref = getattr(record, "artifact_id", None) or getattr(record, "storage_path", None) or str(record)
    context.artifact_refs[name] = ref
    return ref


def persist_json(context: ExecutionContext, *, kind: str, name: str, payload: Any) -> str | None:
    return persist_text(context, kind=kind, name=name, text=json.dumps(jsonable(payload), sort_keys=True, default=str), mime_type="application/json")
