"""High-level LoopEngine facade - the main entry point for the plugin.

Provides a simple interface to initialize, configure, and run the loop
engine in any Kiro project. Implements the full Loop Engineering architecture:

    Layer ①: Agent Loop (observe → decide → execute → receive → verify → continue/stop)
    Layer ②: Verification Loop (auto-verify, retry on failure, escalate)
    Layer ③: Event-driven Loop (fileEdited hook, change coalescing)
    Layer ④: Hill-climbing Loop (trace, memory, pattern analysis)

    Guardrails (Section 05):
    - Path boundary enforcement
    - Destructive command detection (human approval)
    - Timeout/iteration limits
    - Trace, versioning, rollback
    - Results written back for human understanding
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from kiro_loop_engine.constants import (
    DEFAULT_CONTROL_FILE_PATH,
    DEFAULT_HOOK_FILE_PATH,
    MEMORY_FILE_PATH,
    ROLLBACK_DIR,
    TRACE_FILE_PATH,
)
from kiro_loop_engine.execution_engine import ExecutionEngine
from kiro_loop_engine.handlers.base import BaseHandler
from kiro_loop_engine.handlers.code_generator import CodeGeneratorHandler
from kiro_loop_engine.handlers.code_modifier import CodeModifierHandler
from kiro_loop_engine.handlers.maintenance import MaintenanceHandler
from kiro_loop_engine.handlers.test_runner import TestRunnerHandler
from kiro_loop_engine.loop_controller import LoopController
from kiro_loop_engine.parser import Parser
from kiro_loop_engine.result_writer import ResultWriter
from kiro_loop_engine.tracer import Tracer
from kiro_loop_engine.verification import VerificationLoop

logger = logging.getLogger(__name__)


class LoopEngine:
    """High-level plugin interface for the Kiro Loop Engine.

    Implements the complete Loop Engineering architecture from the diagram:

    Minimum Closed Loop (最小闭环):
        观察状态 → 判断下一步 → 调用工具 → 接收结果 → 验证完成 → 继续/停止

    Four-Layer Loop Stack (四层 Loop Stack):
        ① Agent Loop: Handler execution with tools
        ② Verification Loop: Verify → retry → escalate
        ③ Event-driven Loop: fileEdited hook triggering
        ④ Hill-climbing Loop: Trace/eval/memory

    Six Engineering Constructs (六个工程构件):
        - Automations: Hook-based triggering
        - Memory/State: Persistent execution history
        - Connectors: Pluggable handler system
        - Skills: Type-specific handlers (task, test, etc.)

    Guardrails (护栏):
        - Path boundary enforcement
        - Destructive command detection + human approval
        - Timeout/iteration limits
        - Trace, versioning, rollback points
        - Human-readable results

    Usage:
        engine = LoopEngine(project_root="/path/to/project")
        engine.setup()            # Scaffold control file + hook
        engine.on_file_changed()  # Trigger a cycle (usually called by hook)

    You can also register custom handlers:
        engine.register_handler("deploy", MyDeployHandler(project_root))
    """

    def __init__(
        self,
        project_root: str | None = None,
        control_file_path: str | None = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize the loop engine.

        Args:
            project_root: Absolute path to the project root. Defaults to cwd.
            control_file_path: Path to the control file (relative to project_root
                or absolute). Defaults to '.kiro/loop/control.md'.
            max_retries: Maximum retry attempts for failed blocks (Verification Loop).
        """
        if project_root is None:
            project_root = os.getcwd()
        self.project_root = project_root

        if control_file_path is None:
            control_file_path = os.path.join(project_root, DEFAULT_CONTROL_FILE_PATH)
        elif not os.path.isabs(control_file_path):
            control_file_path = os.path.join(project_root, control_file_path)
        self.control_file_path = control_file_path

        # Build components
        self._parser = Parser()
        self._result_writer = ResultWriter()

        # Layer ④: Tracer with memory persistence
        self._tracer = Tracer(project_root)

        # Layer ②: Verification loop
        self._verification = VerificationLoop(project_root, max_retries=max_retries)

        # Default handlers (Engineering Construct: Skills)
        self._handlers: dict[str, BaseHandler] = {
            "task": CodeGeneratorHandler(project_root),
            "change-request": CodeModifierHandler(project_root),
            "test": TestRunnerHandler(project_root),
            "maintenance": MaintenanceHandler(project_root),
        }

        # Layer ①: Execution engine with verification + tracing
        self._execution_engine = ExecutionEngine(
            project_root=project_root,
            handlers=self._handlers,
            tracer=self._tracer,
            verification=self._verification,
        )

        # Layer ③: Event-driven loop controller
        self._controller = LoopController(
            control_file_path=self.control_file_path,
            parser=self._parser,
            execution_engine=self._execution_engine,
            result_writer=self._result_writer,
            tracer=self._tracer,
        )

    def register_handler(self, block_type: str, handler: BaseHandler) -> None:
        """Register a custom handler for a block type (Engineering Construct: Connectors).

        This allows extending the engine with project-specific handlers.

        Args:
            block_type: The instruction block type (e.g., "deploy", "migrate").
            handler: The handler instance.
        """
        self._handlers[block_type] = handler
        self._execution_engine.register_handler(block_type, handler)

    def setup(self) -> dict[str, str]:
        """Scaffold the loop engine files in the project.

        Creates:
        - .kiro/loop/control.md — control file for instruction blocks
        - .kiro/hooks/loop-controller-hook.kiro.hook — Kiro hook for event triggering
        - .kiro/loop/memory.json — execution memory (Layer ④)
        - .kiro/loop/rollback/ — rollback directory (Guardrail)

        Returns:
            Dict with paths to created files/directories.
        """
        created: dict[str, str] = {}

        # Create control file
        control_dir = os.path.dirname(self.control_file_path)
        Path(control_dir).mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.control_file_path):
            Path(self.control_file_path).write_text(
                "# Loop Engineering Control File\n\n"
                "<!-- Add instruction blocks below as H2 sections -->\n"
                "<!-- Each block needs: type, status, priority metadata -->\n"
                "<!-- Supported types: task, change-request, test, maintenance -->\n\n"
                "<!-- Loop Engineering Metadata Fields:\n"
                "     type: task | change-request | test | maintenance\n"
                "     status: pending | in-progress | completed | failed | skipped | retrying | escalated\n"
                "     priority: low | normal | high\n"
                "     safety: confirmed (required for destructive operations)\n"
                "     max-retries: 3 (override default retry count)\n"
                "     verify: <command> (verification command to run after execution)\n"
                "     accept: <criteria> (acceptance criteria for completion)\n"
                "-->\n",
                encoding="utf-8",
            )
            created["control_file"] = self.control_file_path
            logger.info("Created control file: %s", self.control_file_path)

        # Create hook file (Layer ③: Event-driven Loop)
        hook_path = os.path.join(self.project_root, DEFAULT_HOOK_FILE_PATH)
        hook_dir = os.path.dirname(hook_path)
        Path(hook_dir).mkdir(parents=True, exist_ok=True)
        if not os.path.exists(hook_path):
            hook_config = {
                "name": "Loop Controller",
                "version": "1.0.0",
                "description": (
                    "Watches the loop engineering control file for edits and "
                    "triggers the full parse-execute-verify-write cycle."
                ),
                "when": {
                    "type": "fileEdited",
                    "patterns": [DEFAULT_CONTROL_FILE_PATH],
                },
                "then": {
                    "type": "askAgent",
                    "prompt": (
                        "The loop engineering control file has been edited. "
                        "Execute the loop engine cycle: "
                        "from kiro_loop_engine import LoopEngine; "
                        "engine = LoopEngine(); engine.on_file_changed(). "
                        "Process all pending instruction blocks in document order. "
                        "The engine will automatically verify results, retry failures "
                        "(up to 3 attempts), and escalate if retries are exhausted."
                    ),
                },
            }
            Path(hook_path).write_text(
                json.dumps(hook_config, indent=2), encoding="utf-8"
            )
            created["hook_file"] = hook_path
            logger.info("Created hook file: %s", hook_path)

        # Create rollback directory (Guardrail: trace/版本/回滚点)
        rollback_path = os.path.join(self.project_root, ROLLBACK_DIR)
        Path(rollback_path).mkdir(parents=True, exist_ok=True)
        gitkeep = os.path.join(rollback_path, ".gitkeep")
        if not os.path.exists(gitkeep):
            Path(gitkeep).write_text("", encoding="utf-8")
            created["rollback_dir"] = rollback_path

        # Create trace log directory
        trace_dir = os.path.dirname(os.path.join(self.project_root, TRACE_FILE_PATH))
        Path(trace_dir).mkdir(parents=True, exist_ok=True)

        return created

    def on_file_changed(self) -> None:
        """Trigger the parse-execute-verify-write cycle (Layer ③: Event-driven).

        Called by the Kiro hook when the control file is edited.
        """
        self._controller.on_file_changed()

    def process_cycle(self) -> None:
        """Manually trigger one full processing cycle."""
        self._controller.process_cycle()

    def get_trace(self, block_id: str | None = None) -> list:
        """Get execution trace entries (Layer ④: Hill-climbing).

        Args:
            block_id: If provided, returns trace for specific block only.

        Returns:
            List of TraceEntry objects.
        """
        if block_id:
            return self._tracer.get_block_trace(block_id)
        return self._tracer.memory.traces

    def get_memory_stats(self) -> dict:
        """Get execution memory statistics (Layer ④: Hill-climbing).

        Returns:
            Dict with cycle count, block count, retry count, failure patterns.
        """
        mem = self._tracer.memory
        return {
            "total_cycles": mem.total_cycles,
            "total_blocks_processed": mem.total_blocks_processed,
            "total_retries": mem.total_retries,
            "total_rollbacks": mem.total_rollbacks,
            "last_cycle": mem.last_cycle_timestamp,
            "failure_patterns": mem.failure_patterns,
        }

    def rollback(self, rollback_id: str) -> list[str]:
        """Rollback to a previous state (Guardrail: 回滚点).

        Args:
            rollback_id: The rollback point ID to restore.

        Returns:
            List of files that were restored.
        """
        return self._tracer.rollback(rollback_id)

    @property
    def controller(self) -> LoopController:
        """Access the underlying LoopController for advanced usage."""
        return self._controller

    @property
    def execution_engine(self) -> ExecutionEngine:
        """Access the underlying ExecutionEngine for advanced usage."""
        return self._execution_engine

    @property
    def tracer(self) -> Tracer:
        """Access the tracer for inspection (Layer ④)."""
        return self._tracer

    @property
    def verification(self) -> VerificationLoop:
        """Access the verification loop (Layer ②)."""
        return self._verification
