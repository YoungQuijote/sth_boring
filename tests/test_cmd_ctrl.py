import pytest

from sdk_test_agent.cmd_ctrl.controller import CommandController
from sdk_test_agent.cmd_ctrl.dispatcher import ActionDispatcher
from sdk_test_agent.cmd_ctrl.errors import ActionDispatchError, PolicyViolationError
from sdk_test_agent.cmd_ctrl.operator import (
    CollectArtifactsOperator,
    InstallSdkOperator,
    RunPytestOperator,
    RunPythonOperator,
    WriteFileOperator,
)
from sdk_test_agent.cmd_ctrl.policies import ActionPolicy, PathPolicy
from sdk_test_agent.sandbox.models import ExecResult, SandboxSnapshot


class FakeSandbox:
    def create(self):
        return SandboxSnapshot("s1", "created", "img", None, "/workspace", {})

    def prepare_image(self):
        return "img-1"

    def start(self):
        return SandboxSnapshot("s1", "ready", "img", "c1", "/workspace", {})

    def stop(self):
        return None

    def destroy(self):
        return None

    def snapshot(self):
        return SandboxSnapshot("s1", "removed", "img", None, "/workspace", {})

    def put_text(self, path, content):
        self._last_file = (path, content)

    def run_pip(self, argv):
        return ExecResult(exit_code=0, stdout=b"pip", stderr=b"", duration_sec=0.1, meta={"argv": argv})

    def run_python(self, argv):
        return ExecResult(exit_code=0, stdout=b"py", stderr=b"", duration_sec=0.1, meta={"argv": argv})

    def run_pytest(self, targets, extra_args):
        return ExecResult(exit_code=0, stdout=b"pt", stderr=b"", duration_sec=0.1, meta={"targets": targets, "args": extra_args})

    def get_archive(self, path):
        return b"arc", {"path": path}


def test_controller_full_chain() -> None:
    operators = {
        "install_sdk": InstallSdkOperator(),
        "write_file": WriteFileOperator(),
        "run_python": RunPythonOperator(),
        "run_pytest": RunPytestOperator(),
        "collect_artifacts": CollectArtifactsOperator(),
    }
    dispatcher = ActionDispatcher(operators)
    ctl = CommandController(
        sandbox=FakeSandbox(),
        dispatcher=dispatcher,
        action_policy=ActionPolicy(set(operators.keys())),
        path_policy=PathPolicy("/workspace"),
    )

    opened = ctl.open_session()
    assert opened["image_id"] == "img-1"

    assert ctl.execute_action("write_file", {"path": "tests/test_smoke.py", "content": "assert 1"})["ok"] is True
    assert ctl.execute_action("install_sdk", {"mode": "editable", "path": "."})["ok"] is True
    assert ctl.execute_action("run_pytest", {"targets": ["tests/test_smoke.py"], "extra_args": ["-q"]})["ok"] is True
    assert ctl.execute_action("collect_artifacts", {"path": "out"})["ok"] is True

    closed = ctl.close_session()
    assert closed["closed"] is True


def test_dispatcher_unknown_action() -> None:
    dispatcher = ActionDispatcher({})
    with pytest.raises(ActionDispatchError):
        dispatcher.dispatch("missing", {}, FakeSandbox())


def test_path_policy_block_escape() -> None:
    operators = {"write_file": WriteFileOperator()}
    ctl = CommandController(
        sandbox=FakeSandbox(),
        dispatcher=ActionDispatcher(operators),
        action_policy=ActionPolicy(set(operators.keys())),
        path_policy=PathPolicy("/workspace"),
    )
    with pytest.raises(PolicyViolationError):
        ctl.execute_action("write_file", {"path": "../evil.py", "content": ""})
