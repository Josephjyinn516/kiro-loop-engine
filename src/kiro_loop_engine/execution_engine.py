"""Execution Engine for the Kiro Loop Engine.

Routes instruction blocks to the appropriate handler based on type,
enforcing safety guardrails and timeout limits.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from kiro_loop_engine.constants import MAX_TIMEOUT_SECONDS, TEST_TIMEOUT_SECONDS, VALID_TYPES
from kiro_loop_engine.handlers.base import BaseHandler
from kiro_loop_engine.models import InstructionBlock, ResultBlock
from kiro_loop_engine.safety import enforce_timeout, is_destructive, validate_paths


class ExecutionEngine:
    """Routes instruction blocks to handlers and enforces guardrails."""

    def __init__(self, project_root: str, handlers: dict[str, BaseHandler] | None = None) -> None:
        self.project_root = project_root
        self._handlers: dict[str, BaseHandler] = handlers or {}

    def register_handler(self, block_type: str, handler: BaseHandler) -> None:
        """Register a handler for a specific block type."""
        self._handlers[block_type] = handler

    def execute(self, block: InstructionBlock) -> ResultBlock:
        """Execute a single instruction block with timeout and safety checks."""
        block.status = "in-progress"

        # Validate file paths
        if block.file_paths:
            outside_paths = validate_paths(block.file_paths, self.project_root)
            if outside_paths:
                return self._make_result(
                    status="failed",
                    summary="Path validation failed: paths outside project boundary.",
                    output=f"The following paths are outside the allowed project boundary: {', '.join(outside_paths)}",
                )

        # Check for destructive commands
        if not block.safety_confirmed and block.description:
            if is_destructive(block.description):
                return self._make_result(
                    status="failed",
                    summary="Destructive command detected without safety confirmation.",
                    output=(
                        "The instruction description contains a potentially destructive command. "
                        "Add 'safety: confirmed' to the instruction block to allow execution."
                    ),
                )

        # Validate block type
        if block.type not in VALID_TYPES:
            return self._make_result(
                status="failed",
                summary=f"Invalid block type: '{block.type}'.",
                output=f"Unrecognized type '{block.type}'. Supported types: {', '.join(VALID_TYPES)}",
            )

        handler = self._handlers.get(block.type)
        if handler is None:
            return self._make_result(
                status="failed",
                summary=f"No handler registered for type '{block.type}'.",
                output=f"The execution engine has no handler for block type '{block.type}'.",
            )

        # Check for ambiguous instructions
        if self._is_ambiguous(block):
            return self._make_result(
                status="failed",
                summary="Ambiguous instruction: cannot determine action.",
                output=(
                    "The instruction is too vague to produce a single actionable interpretation. "
                    "Please provide more specific details."
                ),
            )

        # Route to handler with timeout
        timeout = self._get_timeout(block)
        try:
            result = enforce_timeout(handler.execute, timeout, block)
            return result
        except TimeoutError:
            return self._make_result(
                status="failed",
                summary=f"Execution timed out after {timeout} seconds.",
                output=f"The operation exceeded the maximum allowed execution time of {timeout} seconds.",
            )
        except Exception as exc:
            return self._make_result(
                status="failed",
                summary="Execution failed with an unexpected error.",
                output=str(exc)[:2000],
            )

    def _get_timeout(self, block: InstructionBlock) -> int:
        if block.type == "test":
            return TEST_TIMEOUT_SECONDS
        return MAX_TIMEOUT_SECONDS

    def _is_ambiguous(self, block: InstructionBlock) -> bool:
        has_description = bool(block.description and block.description.strip())
        has_file_paths = bool(block.file_paths)

        if not has_description and not has_file_paths:
            return True
        if has_description and len(block.description.strip()) < 10 and not has_file_paths:
            return True
        return False

    def _make_result(self, status: str, summary: str, output: str) -> ResultBlock:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        truncated = False
        if len(summary) > 500:
            summary = summary[:497] + "..."
            truncated = True
        if len(output) > 2000:
            output = output[:1997] + "..."
            truncated = True

        return ResultBlock(
            timestamp=timestamp,
            status=status,
            summary=summary,
            output=output,
            truncated=truncated,
        )
