"""Loop Controller for the Kiro Loop Engine.

Orchestrates the parse-execute-write cycle triggered by file change
events from the Kiro fileEdited hook.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from kiro_loop_engine.constants import COALESCE_WINDOW_MS, VALID_STATUSES, VALID_TYPES
from kiro_loop_engine.execution_engine import ExecutionEngine
from kiro_loop_engine.models import InstructionBlock, ResultBlock
from kiro_loop_engine.parser import Parser
from kiro_loop_engine.result_writer import ResultWriter

logger = logging.getLogger(__name__)


class LoopController:
    """Orchestrates the parse-execute-write cycle.

    Triggered by Kiro's fileEdited hook when the control file is saved.
    Reads the file, parses instruction blocks, processes pending blocks
    in document order, and writes results back.
    """

    def __init__(
        self,
        control_file_path: str = ".kiro/loop/control.md",
        parser: Parser | None = None,
        execution_engine: ExecutionEngine | None = None,
        result_writer: ResultWriter | None = None,
    ) -> None:
        self.control_file_path: str = control_file_path
        self.change_queue: list[float] = []
        self.is_processing: bool = False
        self.coalesce_window_ms: int = COALESCE_WINDOW_MS
        self._paused: bool = False

        self._parser: Parser = parser or Parser()
        self._execution_engine: ExecutionEngine | None = execution_engine
        self._result_writer: ResultWriter = result_writer or ResultWriter()

    def on_file_changed(self) -> None:
        """Hook callback. Queues the change event and triggers processing if idle."""
        now = time.time()
        self.change_queue.append(now)

        if self.is_processing:
            logger.debug("Change queued during active processing.")
            return

        if not Path(self.control_file_path).exists():
            logger.warning("Control file '%s' not found. Pausing.", self.control_file_path)
            self._paused = True
            return

        if self._paused:
            logger.info("Control file '%s' recreated. Resuming.", self.control_file_path)
            self._paused = False
            self.change_queue.clear()
            self.change_queue.append(time.time())

        if self._coalesce_changes():
            logger.debug("Change coalesced into pending burst.")
            return

        self.process_cycle()

    def process_cycle(self) -> None:
        """Read, parse, execute pending blocks in document order, write results."""
        self.is_processing = True
        self.change_queue.clear()

        try:
            self._run_cycle()
        except Exception as exc:
            logger.error("Unrecoverable error during processing cycle: %s", exc)
            self._handle_unrecoverable_error(exc)
        finally:
            self.is_processing = False

        if self.change_queue:
            logger.info("Processing queued changes detected during previous cycle.")
            if not self._coalesce_changes():
                self.process_cycle()

    def _run_cycle(self) -> None:
        control_path = Path(self.control_file_path)
        if not control_path.exists():
            self._paused = True
            return

        file_content = control_path.read_text(encoding="utf-8")
        blocks = self._parser.parse(file_content)

        if not blocks:
            return

        processed_titles: set[str] = set()

        while True:
            target_block: InstructionBlock | None = None
            unrecognized_block: InstructionBlock | None = None

            for block in blocks:
                if block.title in processed_titles:
                    continue
                if block.status == "pending":
                    target_block = block
                    break
                elif block.status not in VALID_STATUSES:
                    unrecognized_block = block
                    break

            if target_block is None and unrecognized_block is None:
                break

            if target_block is not None:
                processed_titles.add(target_block.title)
                file_content = self._process_block(target_block, file_content)
            elif unrecognized_block is not None:
                processed_titles.add(unrecognized_block.title)
                file_content = self._handle_unrecognized_status(unrecognized_block, file_content)

            blocks = self._parser.parse(file_content)

    def _process_block(self, block: InstructionBlock, file_content: str) -> str:
        validation_errors = self._parser.validate_block(block)

        if validation_errors:
            result = self._make_validation_error_result(block, validation_errors)
            file_content = self._write_result(file_content, block, result)
            return file_content

        if block.type and block.type not in VALID_TYPES:
            result = ResultBlock(
                timestamp=self._now_timestamp(),
                status="failed",
                summary=f"Invalid block type: '{block.type}'.",
                output=f"Unrecognized type '{block.type}'. Supported types: {', '.join(VALID_TYPES)}",
                truncated=False,
            )
            file_content = self._write_result(file_content, block, result)
            return file_content

        if self._execution_engine is None:
            result = ResultBlock(
                timestamp=self._now_timestamp(),
                status="failed",
                summary="No execution engine configured.",
                output="The LoopController has no execution engine registered.",
                truncated=False,
            )
        else:
            try:
                result = self._execution_engine.execute(block)
            except Exception as exc:
                result = ResultBlock(
                    timestamp=self._now_timestamp(),
                    status="failed",
                    summary="Execution failed with an unexpected error.",
                    output=str(exc)[:2000],
                    truncated=len(str(exc)) > 2000,
                )

        file_content = self._write_result(file_content, block, result)
        return file_content

    def _handle_unrecognized_status(self, block: InstructionBlock, file_content: str) -> str:
        result = ResultBlock(
            timestamp=self._now_timestamp(),
            status="skipped",
            summary=f"Warning: unrecognized status '{block.status}'.",
            output=f"The status value '{block.status}' is not recognized. Valid: {', '.join(VALID_STATUSES)}.",
            truncated=False,
        )
        file_content = self._write_result(file_content, block, result)
        return file_content

    def _make_validation_error_result(self, block: InstructionBlock, errors: list[str]) -> ResultBlock:
        missing_fields = [e for e in errors if "Missing required field" in e]
        type_errors = [e for e in errors if "Unrecognized type" in e]

        if missing_fields:
            summary = f"Block validation failed: {'; '.join(missing_fields)}"
        elif type_errors:
            summary = f"Invalid block type: '{block.type}'."
        else:
            summary = "Block validation failed."

        return ResultBlock(
            timestamp=self._now_timestamp(),
            status="failed",
            summary=summary[:500],
            output="\n".join(errors)[:2000],
            truncated=False,
        )

    def _write_result(self, file_content: str, block: InstructionBlock, result: ResultBlock) -> str:
        updated_content = self._result_writer.write_result(file_content, block, result)
        self._result_writer.save(self.control_file_path, updated_content)
        return updated_content

    def _coalesce_changes(self) -> bool:
        if len(self.change_queue) < 2:
            return False
        first_change = self.change_queue[0]
        last_change = self.change_queue[-1]
        window_seconds = self.coalesce_window_ms / 1000.0
        return (last_change - first_change) < window_seconds

    def _handle_unrecoverable_error(self, exc: Exception) -> None:
        try:
            control_path = Path(self.control_file_path)
            if control_path.exists():
                content = control_path.read_text(encoding="utf-8")
                error_section = (
                    f"\n\n## Loop Controller Error\n\n"
                    f"timestamp: {self._now_timestamp()}\n"
                    f"error: {str(exc)[:2000]}\n"
                )
                content += error_section
                self._result_writer.save(self.control_file_path, content)
        except Exception as write_exc:
            logger.error("Failed to write error to control file: %s", write_exc)

    def _now_timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
