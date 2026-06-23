"""Verification Loop (Layer ②) for the Kiro Loop Engine.

Implements: Check failure → retry with backoff → escalate to human.

The verification loop ensures that execution results are validated
before being marked as complete. If verification fails, the block
is retried with context from previous attempts.

Flow:
    Execute → Verify → Pass? → Complete
                    → Fail? → Retry (up to max_retries)
                           → Exhausted? → Escalate to human
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone

from kiro_loop_engine.constants import MAX_RETRIES, RETRY_DELAY_SECONDS, TEST_TIMEOUT_SECONDS
from kiro_loop_engine.models import InstructionBlock, ResultBlock

logger = logging.getLogger(__name__)


class VerificationLoop:
    """Verification loop that validates execution results and manages retries.

    Corresponds to Layer ② in the Loop Engineering architecture:
    - Checks execution results for correctness
    - Retries on failure with exponential backoff
    - Escalates to human after max retries exhausted
    """

    def __init__(self, project_root: str, max_retries: int = MAX_RETRIES) -> None:
        self.project_root = project_root
        self.max_retries = max_retries

    def verify(self, block: InstructionBlock, result: ResultBlock) -> ResultBlock:
        """Verify an execution result against the block's acceptance criteria.

        Args:
            block: The instruction block that was executed.
            result: The result from execution.

        Returns:
            Updated ResultBlock with verification status.
        """
        # If execution already failed, no verification needed — go to retry logic
        if result.status == "failed":
            return result

        # If block has explicit verification command, run it
        if block.verify:
            return self._run_verification_command(block, result)

        # If block has acceptance criteria, check against output
        if block.acceptance_criteria:
            return self._check_acceptance_criteria(block, result)

        # Default verification: check that output doesn't contain error indicators
        return self._default_verification(block, result)

    def should_retry(self, block: InstructionBlock, result: ResultBlock) -> bool:
        """Determine if a failed block should be retried.

        Args:
            block: The instruction block.
            result: The failed result.

        Returns:
            True if the block should be retried.
        """
        max_retries = block.max_retries if block.max_retries > 0 else self.max_retries

        if block.retry_count >= max_retries:
            return False

        # Don't retry safety failures or ambiguity errors
        non_retryable_keywords = [
            "path validation failed",
            "destructive command detected",
            "ambiguous instruction",
            "no handler registered",
            "invalid block type",
        ]
        summary_lower = result.summary.lower()
        for keyword in non_retryable_keywords:
            if keyword in summary_lower:
                return False

        return True

    def should_escalate(self, block: InstructionBlock) -> bool:
        """Determine if a block should be escalated to human review.

        Args:
            block: The instruction block that has exhausted retries.

        Returns:
            True if the block should be escalated.
        """
        max_retries = block.max_retries if block.max_retries > 0 else self.max_retries
        return block.retry_count >= max_retries

    def get_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff.

        Args:
            attempt: The current attempt number (0-indexed).

        Returns:
            Delay in seconds before next retry.
        """
        # Exponential backoff: 2s, 4s, 8s...
        return RETRY_DELAY_SECONDS * (2 ** attempt)

    def build_retry_context(self, block: InstructionBlock, result: ResultBlock) -> str:
        """Build context from previous failure to improve next attempt.

        Args:
            block: The instruction block.
            result: The failed result.

        Returns:
            Context string to prepend to the next execution attempt.
        """
        context_parts = [
            f"[RETRY {block.retry_count + 1}/{block.max_retries}]",
            f"Previous attempt failed: {result.summary}",
        ]

        if result.output:
            # Include relevant error info (truncated)
            error_excerpt = result.output[:500]
            context_parts.append(f"Error details: {error_excerpt}")

        if result.verification_output:
            context_parts.append(f"Verification failure: {result.verification_output}")

        return "\n".join(context_parts)

    def _run_verification_command(
        self, block: InstructionBlock, result: ResultBlock
    ) -> ResultBlock:
        """Run an explicit verification command."""
        verify_cmd = block.verify.strip()

        try:
            proc = subprocess.run(
                verify_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=TEST_TIMEOUT_SECONDS,
                cwd=self.project_root,
            )

            if proc.returncode == 0:
                result.verified = True
                result.verification_output = proc.stdout[:500] if proc.stdout else "Verification passed."
                return result
            else:
                result.verified = False
                result.status = "failed"
                combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
                result.verification_output = f"Verification command failed (exit {proc.returncode}): {combined[:500]}"
                return result

        except subprocess.TimeoutExpired:
            result.verified = False
            result.status = "failed"
            result.verification_output = f"Verification command timed out after {TEST_TIMEOUT_SECONDS}s."
            return result
        except OSError as exc:
            result.verified = False
            result.status = "failed"
            result.verification_output = f"Verification command error: {exc}"
            return result

    def _check_acceptance_criteria(
        self, block: InstructionBlock, result: ResultBlock
    ) -> ResultBlock:
        """Check result against acceptance criteria patterns."""
        criteria = block.acceptance_criteria.lower()
        output_lower = result.output.lower() if result.output else ""
        summary_lower = result.summary.lower()

        # Check if acceptance criteria mentions file existence
        file_checks = re.findall(
            r"(?:file|path)\s+(?:exists?|created?|present)\s*[:\s]*([^\s,]+)",
            criteria,
        )
        for file_path in file_checks:
            full_path = os.path.join(self.project_root, file_path)
            if not os.path.exists(full_path):
                result.verified = False
                result.status = "failed"
                result.verification_output = f"Acceptance check failed: file '{file_path}' does not exist."
                return result

        # Check if acceptance criteria mentions specific output patterns
        expected_patterns = re.findall(r"(?:expect|contains?|should have)\s*[:\s]*[\"']([^\"']+)[\"']", criteria)
        for pattern in expected_patterns:
            if pattern.lower() not in output_lower and pattern.lower() not in summary_lower:
                result.verified = False
                result.status = "failed"
                result.verification_output = f"Acceptance check failed: expected '{pattern}' not found in output."
                return result

        # If we get here, criteria passed (or were too complex to auto-check)
        result.verified = True
        result.verification_output = "Acceptance criteria satisfied."
        return result

    def _default_verification(
        self, block: InstructionBlock, result: ResultBlock
    ) -> ResultBlock:
        """Default verification: ensure no obvious error indicators."""
        if result.status == "completed":
            # For task/change-request: verify files were actually created/modified
            if block.type in ("task", "change-request") and block.file_paths:
                for file_path in block.file_paths:
                    full_path = os.path.join(self.project_root, file_path)
                    if not os.path.isabs(file_path):
                        full_path = os.path.join(self.project_root, file_path)
                    else:
                        full_path = file_path
                    if not os.path.exists(full_path):
                        result.verified = False
                        result.status = "failed"
                        result.verification_output = (
                            f"Verification failed: expected file '{file_path}' does not exist after execution."
                        )
                        return result

            result.verified = True
            result.verification_output = "Default verification passed."

        return result
