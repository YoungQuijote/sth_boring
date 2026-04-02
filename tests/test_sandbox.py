from mcped_function_tools import PythonSandbox, SandboxLimits


def test_sandbox_success_and_input() -> None:
    sandbox = PythonSandbox(limits=SandboxLimits(timeout_seconds=1.0, memory_mb=128))
    result = sandbox.run("print(INPUT['a'] + 2)", input_data={"a": 40})

    assert result.ok is True
    assert result.timed_out is False
    assert result.exit_code == 0
    assert result.stdout.strip() == "42"


def test_sandbox_timeout() -> None:
    sandbox = PythonSandbox(limits=SandboxLimits(timeout_seconds=0.2, memory_mb=128))
    result = sandbox.run("while True:\n    pass")

    assert result.ok is False
    assert result.timed_out is True
    assert result.exit_code is None


def test_sandbox_stderr() -> None:
    sandbox = PythonSandbox(limits=SandboxLimits(timeout_seconds=1.0, memory_mb=128))
    result = sandbox.run("raise ValueError('boom')")

    assert result.ok is False
    assert result.timed_out is False
    assert result.exit_code != 0
    assert "ValueError" in result.stderr
