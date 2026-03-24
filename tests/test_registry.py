from mcped_function_tools import ToolRegistry, ToolSpec
from mcped_function_tools.mcp_adapter import MCPFunctionAdapter


def test_register_list_and_call() -> None:
    reg = ToolRegistry()
    reg.register(
        ToolSpec(
            name="sum_two",
            description="sum two numbers",
            input_schema={"type": "object"},
            handler=lambda args: {"result": args["a"] + args["b"]},
            tags=["math"],
        )
    )

    tools = reg.list_tools(tag="math")
    assert len(tools) == 1
    assert tools[0].name == "sum_two"

    out = reg.call("sum_two", {"a": 1, "b": 2})
    assert out.ok is True
    assert out.content == {"result": 3}


def test_unknown_and_error_path() -> None:
    reg = ToolRegistry()

    unknown = reg.call("missing", {})
    assert unknown.ok is False
    assert "Unknown tool" in (unknown.error or "")

    reg.register(
        ToolSpec(
            name="boom",
            description="always raises",
            input_schema={"type": "object"},
            handler=lambda args: 1 / 0,
        )
    )

    broken = reg.call("boom", {})
    assert broken.ok is False
    assert "division" in (broken.error or "")


def test_mcp_adapter() -> None:
    reg = ToolRegistry()
    reg.register(
        ToolSpec(
            name="echo",
            description="echo back",
            input_schema={"type": "object"},
            handler=lambda args: {"echo": args.get("text")},
        )
    )

    adapter = MCPFunctionAdapter(reg)
    listed = adapter.list_tools()
    assert listed["tools"][0]["name"] == "echo"

    success = adapter.call_tool("echo", {"text": "x"})
    assert success["isError"] is False

    failure = adapter.call_tool("nope", {})
    assert failure["isError"] is True
