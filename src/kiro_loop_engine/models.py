"""Core data models for the Kiro Loop Engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResultBlock:
    """Structured representation of execution results.

    Written back into the control file as an H3 sub-section after
    an instruction block is processed.
    """

    timestamp: str  # ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
    status: str  # completed | failed | skipped
    summary: str  # Max 500 characters
    output: str  # Max 2000 characters, truncated if needed
    truncated: bool  # Whether output was truncated


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
