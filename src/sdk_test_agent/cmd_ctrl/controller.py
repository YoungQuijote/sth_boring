from __future__ import annotations

from .dispatcher import ActionDispatcher
from .errors import CommandControlError, OperatorExecutionError
from dataclasses import asdict

from .models import ActionResponse
from .policies import ActionPolicy, PathPolicy


class CommandController:
    def __init__(
        self,
        sandbox,
        dispatcher: ActionDispatcher,
        action_policy: ActionPolicy | None = None,
        path_policy: PathPolicy | None = None,
    ) -> None:
        self.sandbox = sandbox
        self.dispatcher = dispatcher
        self.action_policy = action_policy
        self.path_policy = path_policy

    def open_session(self) -> dict:
        created = self.sandbox.create()
        image_id = self.sandbox.prepare_image()
        started = self.sandbox.start()
        return {
            "created": created,
            "image_id": image_id,
            "started": started,
        }

    def execute_action(self, action: str, payload: dict) -> dict:
        try:
            if self.action_policy is not None:
                self.action_policy.validate_action(action)
            if self.path_policy is not None and action in {"write_file", "collect_artifacts"}:
                path = payload.get("path", "")
                self.path_policy.validate_relative_path(path)

            data = self.dispatcher.dispatch(action, payload, self.sandbox)
            return asdict(ActionResponse(ok=True, action=action, data=data))
        except CommandControlError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise OperatorExecutionError(f"action={action} failed: {exc}") from exc

    def close_session(self) -> dict:
        self.sandbox.stop()
        self.sandbox.destroy()
        return {"closed": True, "snapshot": self.sandbox.snapshot()}
