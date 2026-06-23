"""Execution Engine for the Kiro Loop Engine.

Implements the full Loop Engineering Agent Loop (Layer ①):
    Observe → Decide → Execute → Verify → Continue/Stop

Routes instruction blocks to the appropriate handler based on type,
enforcing safety guardrails, timeout limits, verification, and retry logic.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from kiro_loop_engine.constants import (
    MAX_RETRIES,
    MAX_TIMEOUT_SECONDS,
    RETRY_DELAY_SECONDS,
    TEST_TIMEOUT_SECONDS,
    VALID_TYPES,
)
from kiro_loop_engine.handlers.base import BaseHandler
from kiro_loop_engine.models import InstructionBlock, ResultBlock
from kiro_loop_engine.safety import enforce_timeout, is_destructive, validate_paths
from kiro_loop_engine.tracer import Tracer
from kiro_loop_engine.verification import VerificationLoop


class ExecutionEngine:
    """Routes instruction blocks to handlers with full loop architecture.

    Implements the complete Agent Loop (Layer ①):
    1. Observe: Receive instruction block
    2. Decide: Validate, safety check, select handler
    3. Execute: Run handler with timeout
    4. Verify: Validate result (Layer ②)
    5. Continue/Stop: Retry on failure or mark complete

    Integrates with:
    - Verification Loop (Layer ②): Auto-retry on verification failure
    - Tracer (Layer ④): Records all actions for hill-climbing
    - Safety guardrails (Section 05): Path validation, destructive detection, timeouts
    """

    def __init__(
        self,
        project_root: str,
        handlers: dict[str, BaseHandler] | None = None,
        tracer: Tracer | None = None,
        verification: VerificationLoop | None = None,
    ) -> None:
        self.project_root = project_root
        self._handlers: dict[str, BaseHandler] = handlers or {}
        self._tracer = tracer or Tracer(project_root)
        self._verification = verification or VerificationLoop(project_root)

    @property
    def tracer(self) -> Tracer:
        """Access the execution tracer."""
        return self._tracer

    def register_handler(self, block_type: str, handler: BaseHandler) -> None:
        """Register a handler for a specific block type."""
        self._handlers[block_type] = handler

    def execute(self, block: InstructionBlock) -> ResultBlock:
        """Execute a single instruction block with the full loop architecture.

        Flow:
            1. Safety pre-checks (guardrails)
            2. Execute handler
            3. Verify result (verification loop)
            4. If failed and retryable → retry with backoff
            5. If retries exhausted → escalate
            6. Record trace (hill-climbing)
        """
        block.status = "in-progress"

        # === GUARDRAILS: Pre-execution safety checks ===
        safety_result = self._safety_checks(block)
        if safety_result is not None:
            self._tracer.record(
                block_id=block.id,
                block_title=block.title,
                attempt=block.retry_count + 1,
                action="execute",
                handler_type=block.type,
                input_summary=block.description[:200] if block.description else "",
                output_summary=safety_result.summary,
                status="failed",
                error=safety_result.summary,
            )
            return safety_result

        # === AGENT LOOP: Execute with verification and retry ===
        return self._execute_with_retry(block)

    def _execute_with_retry(self, block: InstructionBlock) -> ResultBlock:
        """Execute block with verification loop and retry logic (Layers ① + ②)."""
        max_retries = block.max_retries if block.max_retries > 0 else MAX_RETRIES

        while True:
            attempt = block.retry_count + 1
            start_time = time.time()

            # Create rollback point before execution (Guardrail: rollback)
            rollback_id = None
            if block.file_paths and block.type in ("task", "change-request", "maintenance"):
                rollback_id = self._tracer.create_rollback_point(block.id, block.file_paths)

            # === EXECUTE ===
            result = self._execute_handler(block)
            duration_ms = int((time.time() - start_time) * 1000)
            result.attempt = attempt

            # === VERIFY (Layer ②) ===
            if result.status != "failed":
                result = self._verification.verify(block, result)

            # === TRACE (Layer ④) ===
            self._tracer.record(
                block_id=block.id,
                block_title=block.title,
                attempt=attempt,
                action="execute" if attempt == 1 else "retry",
                handler_type=block.type,
                input_summary=block.description[:200] if block.description else "",
                output_summary=result.summary[:200],
                status=result.status,
                duration_ms=duration_ms,
                error=result.summary if result.status == "failed" else "",
                files_affected=block.file_paths,
                rollback_available=rollback_id is not None,
            )

            # === DECIDE: Continue or Stop ===
            if result.status == "completed" and result.verified:
                # Success — stop the loop
                self._tracer.memory.total_blocks_processed += 1
                return result

            if result.status == "failed":
                # Check if we should retry
                if self._verification.should_retry(block, result):
                    # Rollback before retry
                    if rollback_id:
                        restored = self._tracer.rollback(rollback_id)
                        self._tracer.record(
                            block_id=block.id,
                            block_title=block.title,
                            attempt=attempt,
                            action="rollback",
                            handler_type=block.type,
                            input_summary=f"Rolling back {len(restored)} files",
                            output_summary=f"Restored: {', '.join(restored[:5])}",
                            status="completed",
                            files_affected=restored,
                        )

                    # Increment retry counter
                    block.retry_count += 1
                    block.status = "retrying"

                    # Apply retry delay with backoff
                    delay = self._verification.get_retry_delay(block.retry_count)
                    time.sleep(min(delay, 10.0))  # Cap at 10s to avoid blocking

                    continue  # Loop back to retry

                else:
                    # Retries exhausted → escalate to human
                    if self._verification.should_escalate(block):
                        result.status = "escalated"
                        result.summary = (
                            f"[ESCALATED] After {attempt} attempt(s): {result.summary}"
                        )
                        self._tracer.record(
                            block_id=block.id,
                            block_title=block.title,
                            attempt=attempt,
                            action="escalate",
                            handler_type=block.type,
                            input_summary="Max retries exhausted, escalating to human",
                            output_summary=result.summary[:200],
                            status="escalated",
                        )

                    return result

            # If status is something unexpected, return as-is
            return result

    def _execute_handler(self, block: InstructionBlock) -> ResultBlock:
        """Execute the appropriate handler with timeout enforcement."""
        handler = self._handlers.get(block.type)
        if handler is None:
            return self._make_result(
                status="failed",
                summary=f"No handler registered for type '{block.type}'.",
                output=f"The execution engine has no handler for block type '{block.type}'.",
            )

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

    def _safety_checks(self, block: InstructionBlock) -> ResultBlock | None:
        """Run pre-execution safety guardrails. Returns a failure result if blocked."""
        # Validate file paths stay within project boundary
        if block.file_paths:
            outside_paths = validate_paths(block.file_paths, self.project_root)
            if outside_paths:
                return self._make_result(
                    status="failed",
                    summary="Path validation failed: paths outside project boundary.",
                    output=f"The following paths are outside the allowed project boundary: {', '.join(outside_paths)}",
                )

        # Check for destructive commands (requires safety: confirmed)
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

        # Validate block type has a registered handler
        if block.type not in self._handlers:
            return self._make_result(
                status="failed",
                summary=f"No handler registered for type '{block.type}'.",
                output=f"Unrecognized type '{block.type}'. Available: {', '.join(self._handlers.keys())}",
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

        return None  # All checks passed

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
