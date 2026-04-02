from __future__ import annotations

from .cmd_ctrl_errors import ActionDispatchError
from .operator import BaseOperator


class ActionDispatcher:
    def __init__(self, operators: dict[str, BaseOperator]) -> None:
        self.operators = operators

    def dispatch(self, action: str, payload: dict, sandbox) -> dict:
        op = self.operators.get(action)
        if op is None:
            raise ActionDispatchError(f"unknown action: {action}")
        return op.run(sandbox, payload)
