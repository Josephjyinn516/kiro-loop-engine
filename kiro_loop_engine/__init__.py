"""Kiro Loop Engine - Reusable file-driven automation plugin for Kiro IDE.

Usage:
    from kiro_loop_engine import LoopEngine

    # Initialize in your project
    engine = LoopEngine(project_root="/path/to/project")
    engine.setup()          # Creates .kiro/loop/control.md and hook file
    engine.on_file_changed()  # Trigger a parse-execute-write cycle

    # Or use the CLI
    # $ kiro-loop init      # Scaffold loop files in current project
    # $ kiro-loop run       # Manually trigger one cycle
"""

from kiro_loop_engine.constants import (
    COALESCE_WINDOW_MS,
    DESTRUCTIVE_PATTERNS,
    MAX_OUTPUT_LENGTH,
    MAX_RESULT_ROWS,
    MAX_SUMMARY_LENGTH,
    MAX_TIMEOUT_SECONDS,
    TEST_TIMEOUT_SECONDS,
    VALID_PRIORITIES,
    VALID_STATUSES,
    VALID_TYPES,
)
from kiro_loop_engine.engine import LoopEngine
from kiro_loop_engine.execution_engine import ExecutionEngine
from kiro_loop_engine.handlers.base import BaseHandler
from kiro_loop_engine.handlers.code_generator import CodeGeneratorHandler
from kiro_loop_engine.handlers.code_modifier import CodeModifierHandler
from kiro_loop_engine.handlers.maintenance import MaintenanceHandler
from kiro_loop_engine.handlers.test_runner import TestRunnerHandler
from kiro_loop_engine.loop_controller import LoopController
from kiro_loop_engine.models import InstructionBlock, ResultBlock
from kiro_loop_engine.parser import Parser
from kiro_loop_engine.result_writer import ResultWriter

__version__ = "1.0.0"

__all__ = [
    "LoopEngine",
    "LoopController",
    "ExecutionEngine",
    "Parser",
    "ResultWriter",
    "BaseHandler",
    "CodeGeneratorHandler",
    "CodeModifierHandler",
    "MaintenanceHandler",
    "TestRunnerHandler",
    "InstructionBlock",
    "ResultBlock",
    "VALID_TYPES",
    "VALID_STATUSES",
    "VALID_PRIORITIES",
]
