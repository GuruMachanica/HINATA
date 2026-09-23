"""Tests for tool parameter validation and security sandboxing."""
from backend.features.tools.base import ToolRiskLevel  # noqa: F401
from backend.features.tools.builtin.shell_tool import PythonEvalTool, ShellTool
from backend.features.tools.builtin.system_tools import SystemInfoTool
from backend.features.tools.registry import ToolRegistry


def test_tool_param_validation():
    print("[1/6] Testing ToolParam & Tool.validate()...")
    reg = ToolRegistry()
    shell = ShellTool()
    py = PythonEvalTool()
    reg.register_all(shell, py)

    # Shell requires 'command'
    err = shell.validate({})
    assert err and "missing required param 'command'" in err, f"Expected missing required param, got: {err}"

    # Shell bounds on timeout: 1 to 60
    err_low = shell.validate({"command": "git status", "timeout": -5})
    assert err_low and ">= 1" in err_low, f"Expected timeout >= 1 error, got: {err_low}"

    err_high = shell.validate({"command": "git status", "timeout": 999})
    assert err_high and "<= 60" in err_high, f"Expected timeout <= 60 error, got: {err_high}"
    print("  -> ToolParam validation PASSED")


def test_shell_tool_security():
    print("[2/6] Testing ShellTool security & whitelisting...")
    shell = ShellTool()

    for bad_cmd, ch in [("git status | dir", "|"), ("python --version; echo hacked", ";"),
                        ("whoami && dir", "&")]:
        r = shell.run(bad_cmd)
        assert not r.ok and f"operator '{ch}' is not allowed" in r.output, \
            f"Chaining '{ch}' was not blocked: {r.output}"

    r4 = shell.run("powershell -Command Get-Process")
    assert not r4.ok and "not in the allowed diagnostic whitelist" in r4.output, \
        f"Powershell was not blocked: {r4.output}"

    r5 = shell.run("del test.txt")
    assert not r5.ok and "not in the allowed diagnostic whitelist" in r5.output, \
        f"del was not blocked: {r5.output}"

    r6 = shell.run("python --version")
    assert r6.ok and "Python" in r6.output, f"python --version failed: {r6.output}"
    print("  -> ShellTool security PASSED")


def test_python_eval_sandbox():
    print("[3/6] Testing PythonEvalTool AST sandbox...")
    py = PythonEvalTool()

    r1 = py.run("2 ** 8 + 14")
    assert r1.ok and r1.output == "270", f"Expected 270, got: {r1.output}"

    r2 = py.run("len([1, 2, 3, 4, 5])")
    assert r2.ok and r2.output == "5", f"Expected 5, got: {r2.output}"

    r3 = py.run("round(3.14159, 2)")
    assert r3.ok and r3.output == "3.14", f"Expected 3.14, got: {r3.output}"

    r4 = py.run("__import__('os').system('dir')")
    assert not r4.ok and "sandbox error" in r4.output, f"__import__ was not blocked: {r4.output}"

    r5 = py.run("().__class__.__bases__[0].__subclasses__()")
    assert not r5.ok and "not permitted" in r5.output, f"Attribute escape was not blocked: {r5.output}"

    r6 = py.run("open('test.txt', 'w')")
    assert not r6.ok and "name 'open' is not defined" in r6.output, f"open was not blocked: {r6.output}"
    print("  -> PythonEvalTool AST sandbox PASSED")


def test_system_info_numeric_metrics():
    print("[4/6] Testing SystemInfoTool numeric metrics...")
    r = SystemInfoTool().run()
    assert r.ok and r.data is not None, f"SystemInfoTool failed: {r.output}"
    assert isinstance(r.data.get("disk_free_gb"), int), "disk_free_gb should be numeric"
    print("  -> SystemInfoTool numeric metrics PASSED")


def test_tool_registry_duplicate_and_dispatch():
    print("[5/6] Testing ToolRegistry registration/dispatch...")
    reg = ToolRegistry()
    reg.register_all(CurrentTimeStub())
    # Duplicate registration overwrites silently (last-wins) — ensure no crash
    reg.register_all(CurrentTimeStub())
    result = reg.dispatch("stub_tool", {})
    assert result.ok, f"dispatch failed: {result.output}"
    print("  -> ToolRegistry PASSED")


def test_risk_levels_present():
    print("[6/6] Testing risk levels are declared on all builtin tools...")
    from backend.features.tools.builtin import _register_all  # noqa: F401
    from backend.features.tools.registry import registry
    for tool in registry.all():
        assert tool.risk_level in (ToolRiskLevel.READ_ONLY, ToolRiskLevel.MUTATING,
                                   ToolRiskLevel.DANGEROUS), f"{tool.name} missing risk level"
    print("  -> Risk levels PASSED")


class CurrentTimeStub:
    """Minimal stub tool for registry tests (avoids name clash with builtin)."""
    name = "stub_tool"
    description = "stub"
    risk_level = ToolRiskLevel.READ_ONLY
    params = []

    def signature(self):
        return f"{self.name}()"

    def run(self, **_):
        from backend.features.tools.base import ToolResult
        return ToolResult(ok=True, output="stub ok")

    def validate(self, args):
        return None
