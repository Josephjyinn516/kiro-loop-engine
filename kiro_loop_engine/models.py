"""Core data models for the Kiro Loop Engine.

Implements the full Loop Engineering architecture:
- InstructionBlock with retry/verification metadata
- ResultBlock with verification signals
- TraceEntry for hill-climbing loop memory
- ExecutionMemory for persistent state across cycles
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResultBlock:
    """Structured representation of execution results.

    Written back into the control file as an H3 sub-section after
    an instruction block is processed.
    """

    timestamp: str  # ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
    status: str  # completed | failed | skipped | needs-verification
    summary: str  # Max 500 characters
    output: str  # Max 2000 characters, truncated if needed
    truncated: bool  # Whether output was truncated
    attempt: int = 1  # Which attempt this result is from
    verified: bool = False  # Whether result passed verification
    verification_output: str = ""  # Output from verification step


@dataclass
class InstructionBlock:
    """Structured representation of a parsed instruction block.

    Each H2 section in the control file becomes one InstructionBlock
    after parsing.
    """

    id: str  # Generated unique identifier
    type: str  # task | change-request | test | maintenance
    title: str  # Required: block title from H2 heading
    description: str  # Optional: body content
    priority: str  # low | normal | high (default: normal)
    status: str  # pending | in-progress | completed | failed | skipped
    file_paths: list[str] = field(default_factory=list)  # Explicit file references
    safety_confirmed: bool = False  # Whether safety: confirmed is present
    raw_start_line: int = 0  # Line number where this block starts in the file
    raw_end_line: int = 0  # Line number where this block ends
    result_block: ResultBlock | None = None  # Existing result if present

    # Loop Engineering extensions
    max_retries: int = 3  # Maximum retry attempts (Verification Loop)
    retry_count: int = 0  # Current retry count
    acceptance_criteria: str = ""  # How to verify completion
    verify: str = ""  # Verification command or check


@dataclass
class TraceEntry:
    """A single entry in the execution trace (Hill-climbing Loop Layer ④).

    Records what happened during execution for evaluation, grading,
    and iterative improvement.
    """

    block_id: str
    block_title: str
    attempt: int
    timestamp: str
    action: str  # "execute" | "verify" | "retry" | "rollback" | "escalate"
    handler_type: str
    input_summary: str  # Truncated description of what was attempted
    output_summary: str  # Truncated result
    status: str  # completed | failed | retrying | escalated
    duration_ms: int = 0
    error: str = ""
    files_affected: list[str] = field(default_factory=list)
    rollback_available: bool = False


@dataclass
class ExecutionMemory:
    """Persistent memory across cycles (Engineering Construct: Memory/State).

    Tracks execution history, patterns of success/failure, and provides
    context for future decisions.
    """

    traces: list[TraceEntry] = field(default_factory=list)
    total_cycles: int = 0
    total_blocks_processed: int = 0
    total_retries: int = 0
    total_rollbacks: int = 0
    last_cycle_timestamp: str = ""
    failure_patterns: dict[str, int] = field(default_factory=dict)  # error_type -> count

    def record_trace(self, entry: TraceEntry) -> None:
        """Add a trace entry and update counters."""
        self.traces.append(entry)
        if entry.action == "retry":
            self.total_retries += 1
        if entry.action == "rollback":
            self.total_rollbacks += 1
        if entry.status == "failed" and entry.error:
            error_key = entry.error[:100]
            self.failure_patterns[error_key] = self.failure_patterns.get(error_key, 0) + 1

    def get_block_history(self, block_id: str) -> list[TraceEntry]:
        """Get all trace entries for a specific block."""
        return [t for t in self.traces if t.block_id == block_id]

    def get_recent_failures(self, limit: int = 10) -> list[TraceEntry]:
        """Get recent failed traces for pattern analysis."""
        failed = [t for t in self.traces if t.status == "failed"]
        return failed[-limit:]

    def should_escalate(self, block_id: str, max_retries: int) -> bool:
        """Determine if a block should be escalated to human review."""
        history = self.get_block_history(block_id)
        retry_count = sum(1 for t in history if t.action == "retry")
        return retry_count >= max_retries
