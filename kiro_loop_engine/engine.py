"""High-level LoopEngine facade - the main entry point for the plugin.

Provides a simple interface to initialize, configure, and run the loop
engine in any Kiro project.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from kiro_loop_engine.constants import DEFAULT_CONTROL_FILE_PATH, DEFAULT_HOOK_FILE_PATH
from kiro_loop_engine.execution_engine import ExecutionEngine
from kiro_loop_engine.handlers.base import BaseHandler
from kiro_loop_engine.handlers.code_generator import CodeGeneratorHandler
from kiro_loop_engine.handlers.code_modifier import CodeModifierHandler
from kiro_loop_engine.handlers.maintenance import MaintenanceHandler
from kiro_loop_engine.handlers.test_runner import TestRunnerHandler
from kiro_loop_engine.loop_controller import LoopController
from kiro_loop_engine.parser import Parser
from kiro_loop_engine.result_writer import ResultWriter

logger = logging.getLogger(__name__)


class LoopEngine:
    """High-level plugin interface for the Kiro Loop Engine.

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
    ) -> None:
        """Initialize the loop engine.

        Args:
            project_root: Absolute path to the project root. Defaults to cwd.
            control_file_path: Path to the control file (relative to project_root
                or absolute). Defaults to '.kiro/loop/control.md'.
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

        # Default handlers
        self._handlers: dict[str, BaseHandler] = {
            "task": CodeGeneratorHandler(project_root),
            "change-request": CodeModifierHandler(project_root),
            "test": TestRunnerHandler(project_root),
            "maintenance": MaintenanceHandler(project_root),
        }

        self._execution_engine = ExecutionEngine(
            project_root=project_root,
            handlers=self._handlers,
        )

        self._controller = LoopController(
            control_file_path=self.control_file_path,
            parser=self._parser,
            execution_engine=self._execution_engine,
            result_writer=self._result_writer,
        )

    def register_handler(self, block_type: str, handler: BaseHandler) -> None:
        """Register a custom handler for a block type.

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
        - .kiro/loop/control.md (empty control file)
        - .kiro/hooks/loop-controller-hook.kiro.hook (Kiro hook config)

        Returns:
            Dict with paths to created files.
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
                "<!-- Supported types: task, change-request, test, maintenance -->\n",
                encoding="utf-8",
            )
            created["control_file"] = self.control_file_path
            logger.info("Created control file: %s", self.control_file_path)

        # Create hook file
        hook_path = os.path.join(self.project_root, DEFAULT_HOOK_FILE_PATH)
        hook_dir = os.path.dirname(hook_path)
        Path(hook_dir).mkdir(parents=True, exist_ok=True)
        if not os.path.exists(hook_path):
            hook_config = {
                "enabled": True,
                "name": "Loop Controller",
                "description": (
                    "Watches the loop engineering control file for edits and "
                    "triggers the parse-execute-write cycle."
                ),
                "version": "1",
                "when": {
                    "type": "fileEdited",
                    "patterns": [DEFAULT_CONTROL_FILE_PATH],
                },
                "then": {
                    "type": "askAgent",
                    "prompt": (
                        "The loop engineering control file has been edited. "
                        "Execute the loop engine cycle by running: "
                        "from kiro_loop_engine import LoopEngine; "
                        "engine = LoopEngine(); engine.on_file_changed(). "
                        "Process all pending instruction blocks in document order."
                    ),
                },
            }
            Path(hook_path).write_text(
                json.dumps(hook_config, indent=2), encoding="utf-8"
            )
            created["hook_file"] = hook_path
            logger.info("Created hook file: %s", hook_path)

        return created

    def on_file_changed(self) -> None:
        """Trigger the parse-execute-write cycle.

        Called by the Kiro hook when the control file is edited.
        """
        self._controller.on_file_changed()

    def process_cycle(self) -> None:
        """Manually trigger one full processing cycle."""
        self._controller.process_cycle()

    @property
    def controller(self) -> LoopController:
        """Access the underlying LoopController for advanced usage."""
        return self._controller

    @property
    def execution_engine(self) -> ExecutionEngine:
        """Access the underlying ExecutionEngine for advanced usage."""
        return self._execution_engine
