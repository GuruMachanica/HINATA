"""Builtin tool registration — import side-effect registers everything."""
from ..registry import registry
from .system_tools import CurrentTimeTool, SystemInfoTool, BatteryTool
from .file_tools import ReadFileTool, ListDirTool, WriteFileTool
from .shell_tool import ShellTool, PythonEvalTool
from .memory_tools import RecallMemoryTool, KnowledgeQueryTool, RememberFactTool


def _register_all() -> None:
    registry.register_all(
        CurrentTimeTool(),
        SystemInfoTool(),
        BatteryTool(),
        ReadFileTool(),
        ListDirTool(),
        WriteFileTool(),
        ShellTool(),
        PythonEvalTool(),
        RecallMemoryTool(),
        KnowledgeQueryTool(),
        RememberFactTool(),
    )


_register_all()
