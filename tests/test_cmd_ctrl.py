import pytest

from sdk_test_agent.cmd_ctrl.controller import CommandController
from sdk_test_agent.cmd_ctrl.dispatcher import ActionDispatcher
from sdk_test_agent.cmd_ctrl.cmd_ctrl_errors import (
    ActionDispatchError,
    GuardDeniedError,
    GuardEscalationRequired,
    PolicyViolationError,
)
from sdk_test_agent.cmd_ctrl.cmd_ctrl_models import GuardDecision
from sdk_test_agent.cmd_ctrl.operator import (
    CollectArtifactsOperator,
    GuardedExecOperator,
    InspectExecOperator,
    InstallSdkOperator,
    RunPytestOperator,
    RunPythonOperator,
    WriteFileOperator,
)
from sdk_test_agent.cmd_ctrl.policies import ActionPolicy, PathPolicy
from sdk_test_agent.sandbox.sandbox_models import ExecResult, ExecSpec, SandboxSnapshot


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

    def exec(self, spec: ExecSpec, timeout_sec: int | None = None):
        out = " ".join(spec.argv).encode()
        return ExecResult(exit_code=0, stdout=out, stderr=b"", duration_sec=0.1, meta={"timeout": timeout_sec})


class AlwaysAllowGuard:
    def evaluate(self, argv, payload):
        return GuardDecision(decision="allow", reason="ok")


class AlwaysDenyGuard:
    def evaluate(self, argv, payload):
        return GuardDecision(decision="deny", reason="blocked")


def _default_operators() -> dict:
    return {
        "install_sdk": InstallSdkOperator(),
        "write_file": WriteFileOperator(),
        "run_python": RunPythonOperator(),
        "run_pytest": RunPytestOperator(),
        "collect_artifacts": CollectArtifactsOperator(),
        "inspect_exec": InspectExecOperator(),
        "guarded_exec": GuardedExecOperator(guard=AlwaysAllowGuard()),
    }


def test_controller_full_chain() -> None:
    operators = _default_operators()
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

    assert ctl.execute_action("inspect_exec", {"argv": ["pwd"]})["ok"] is True
    assert ctl.execute_action("guarded_exec", {"argv": ["ls", "-la", "/workspace"]})["ok"] is True

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


def test_inspect_exec_allow_cases() -> None:
    op = InspectExecOperator()
    sb = FakeSandbox()

    assert op.run(sb, {"argv": ["pwd"]})["exit_code"] == 0
    assert op.run(sb, {"argv": ["tail", "-n", "20", "/workspace/app.log"]})["exit_code"] == 0
    assert op.run(sb, {"argv": ["python", "-V"]})["exit_code"] == 0


def test_inspect_exec_reject_dangerous_cases() -> None:
    op = InspectExecOperator()
    sb = FakeSandbox()

    with pytest.raises(PolicyViolationError):
        op.run(sb, {"argv": ["vi", "x.py"]})

    with pytest.raises(PolicyViolationError):
        op.run(sb, {"argv": ["rm", "-rf", "/tmp/x"]})


def test_guarded_exec_allow_deny_escalate() -> None:
    sb = FakeSandbox()

    allow_op = GuardedExecOperator(guard=AlwaysAllowGuard())
    assert allow_op.run(sb, {"argv": ["ls", "-la", "/workspace"]})["exit_code"] == 0

    deny_op = GuardedExecOperator(guard=AlwaysDenyGuard())
    with pytest.raises(GuardDeniedError):
        deny_op.run(sb, {"argv": ["ls"]})

    default_op = GuardedExecOperator()
    with pytest.raises(GuardEscalationRequired):
        default_op.run(sb, {"argv": ["ls"]})


def test_controller_preserves_guard_exceptions() -> None:
    operators = {"guarded_exec": GuardedExecOperator()}
    ctl = CommandController(
        sandbox=FakeSandbox(),
        dispatcher=ActionDispatcher(operators),
        action_policy=ActionPolicy({"guarded_exec"}),
        path_policy=PathPolicy("/workspace"),
    )

    with pytest.raises(GuardEscalationRequired):
        ctl.execute_action("guarded_exec", {"argv": ["ls"]})
