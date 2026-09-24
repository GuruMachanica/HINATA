"""Builtin tool registration — import side-effect registers everything."""
from ..registry import registry
from .system_tools import CurrentTimeTool, SystemInfoTool, BatteryTool, OpenAppOrUrlTool
from .file_tools import ReadFileTool, ListDirTool, WriteFileTool
from .shell_tool import ShellTool, PythonEvalTool
from .memory_tools import RecallMemoryTool, KnowledgeQueryTool, RememberFactTool, ResetKnowledgeTool
from .web_tools import WebSearchTool
from .vision_tools import SeeScreenTool
from .rag_tools import SemanticSearchTool
from .diagnostics_tools import BundleLogsTool, HealthSummaryTool


def _register_all() -> None:
    registry.register_all(
        CurrentTimeTool(),
        SystemInfoTool(),
        BatteryTool(),
        OpenAppOrUrlTool(),
        WebSearchTool(),
        SeeScreenTool(),
        ReadFileTool(),
        ListDirTool(),
        WriteFileTool(),
        ShellTool(),
        PythonEvalTool(),
        RecallMemoryTool(),
        SemanticSearchTool(),
        BundleLogsTool(),
        HealthSummaryTool(),
        KnowledgeQueryTool(),
        RememberFactTool(),
        ResetKnowledgeTool(),
    )


_register_all()
