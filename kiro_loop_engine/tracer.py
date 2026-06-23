"""Trace & Rollback system (Layer ④ + Guardrail: trace/版本/回滚点).

Provides:
- Execution tracing: records every action for audit and hill-climbing
- File rollback: creates backups before modifications, supports undo
- Memory persistence: saves/loads execution history across sessions

This implements two parts of the Loop Engineering architecture:
1. Hill-climbing Loop (Layer ④): trace/eval with memory of past executions
2. Guardrail (trace、版本、回滚点): versioning and rollback capability
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from kiro_loop_engine.constants import (
    MAX_MEMORY_FILE_SIZE,
    MAX_TRACE_ENTRIES,
    MEMORY_FILE_PATH,
    ROLLBACK_DIR,
    TRACE_FILE_PATH,
)
from kiro_loop_engine.models import ExecutionMemory, TraceEntry

logger = logging.getLogger(__name__)


class Tracer:
    """Execution tracer and rollback manager.

    Records all execution actions into a trace log and memory file,
    enabling:
    - Audit trail of all operations
    - Rollback to pre-execution state
    - Pattern analysis for hill-climbing optimization
    - Human-readable trace for understanding what happened
    """

    def __init__(self, project_root: str) -> None:
        self.project_root = project_root
        self._memory = ExecutionMemory()
        self._trace_file = os.path.join(project_root, TRACE_FILE_PATH)
        self._memory_file = os.path.join(project_root, MEMORY_FILE_PATH)
        self._rollback_dir = os.path.join(project_root, ROLLBACK_DIR)

        # Load existing memory if available
        self._load_memory()

    @property
    def memory(self) -> ExecutionMemory:
        """Access the execution memory."""
        return self._memory

    def record(
        self,
        block_id: str,
        block_title: str,
        attempt: int,
        action: str,
        handler_type: str,
        input_summary: str,
        output_summary: str,
        status: str,
        duration_ms: int = 0,
        error: str = "",
        files_affected: list[str] | None = None,
        rollback_available: bool = False,
    ) -> TraceEntry:
        """Record a trace entry for an execution action.

        Args:
            block_id: Unique identifier of the block.
            block_title: Human-readable block title.
            attempt: Attempt number (1-indexed).
            action: Action type (execute, verify, retry, rollback, escalate).
            handler_type: Which handler processed this block.
            input_summary: What was attempted (truncated).
            output_summary: What resulted (truncated).
            status: Result status (completed, failed, retrying, escalated).
            duration_ms: Execution duration in milliseconds.
            error: Error message if applicable.
            files_affected: List of files that were modified.
            rollback_available: Whether rollback is possible.

        Returns:
            The created TraceEntry.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        entry = TraceEntry(
            block_id=block_id,
            block_title=block_title,
            attempt=attempt,
            timestamp=timestamp,
            action=action,
            handler_type=handler_type,
            input_summary=input_summary[:200],
            output_summary=output_summary[:200],
            status=status,
            duration_ms=duration_ms,
            error=error[:500],
            files_affected=files_affected or [],
            rollback_available=rollback_available,
        )

        self._memory.record_trace(entry)
        self._append_trace_log(entry)
        self._prune_memory()
        self._save_memory()

        return entry

    def create_rollback_point(self, block_id: str, file_paths: list[str]) -> str | None:
        """Create a rollback point by backing up files before modification.

        Args:
            block_id: The block ID this rollback point is for.
            file_paths: Files to backup.

        Returns:
            Rollback point ID (directory name), or None if nothing to backup.
        """
        if not file_paths:
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rollback_id = f"{block_id}_{timestamp}"
        rollback_path = os.path.join(self._rollback_dir, rollback_id)

        backed_up: list[str] = []
        for file_path in file_paths:
            full_path = file_path if os.path.isabs(file_path) else os.path.join(self.project_root, file_path)
            if os.path.exists(full_path):
                # Create relative directory structure in rollback
                rel_path = os.path.relpath(full_path, self.project_root)
                backup_path = os.path.join(rollback_path, rel_path)
                Path(os.path.dirname(backup_path)).mkdir(parents=True, exist_ok=True)
                shutil.copy2(full_path, backup_path)
                backed_up.append(rel_path)

        if backed_up:
            # Write manifest
            manifest = {
                "block_id": block_id,
                "timestamp": timestamp,
                "files": backed_up,
            }
            manifest_path = os.path.join(rollback_path, "_manifest.json")
            Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            logger.info("Created rollback point: %s (%d files)", rollback_id, len(backed_up))
            return rollback_id

        return None

    def rollback(self, rollback_id: str) -> list[str]:
        """Restore files from a rollback point.

        Args:
            rollback_id: The rollback point ID to restore from.

        Returns:
            List of files that were restored.
        """
        rollback_path = os.path.join(self._rollback_dir, rollback_id)
        manifest_path = os.path.join(rollback_path, "_manifest.json")

        if not os.path.exists(manifest_path):
            logger.error("Rollback point not found: %s", rollback_id)
            return []

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        restored: list[str] = []
        for rel_path in manifest.get("files", []):
            backup_file = os.path.join(rollback_path, rel_path)
            target_file = os.path.join(self.project_root, rel_path)

            if os.path.exists(backup_file):
                Path(os.path.dirname(target_file)).mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, target_file)
                restored.append(rel_path)

        logger.info("Rolled back %d files from point: %s", len(restored), rollback_id)
        return restored

    def get_block_trace(self, block_id: str) -> list[TraceEntry]:
        """Get full execution trace for a specific block."""
        return self._memory.get_block_history(block_id)

    def get_failure_patterns(self) -> dict[str, int]:
        """Get patterns of recurring failures for analysis."""
        return dict(self._memory.failure_patterns)

    def start_cycle(self) -> None:
        """Mark the start of a new processing cycle."""
        self._memory.total_cycles += 1
        self._memory.last_cycle_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _append_trace_log(self, entry: TraceEntry) -> None:
        """Append a trace entry to the human-readable trace log."""
        Path(os.path.dirname(self._trace_file)).mkdir(parents=True, exist_ok=True)

        log_line = (
            f"[{entry.timestamp}] {entry.action.upper():>10} | "
            f"block={entry.block_title[:40]:<40} | "
            f"attempt={entry.attempt} | "
            f"status={entry.status} | "
            f"handler={entry.handler_type} | "
            f"duration={entry.duration_ms}ms"
        )
        if entry.error:
            log_line += f" | error={entry.error[:100]}"

        try:
            with open(self._trace_file, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except OSError as exc:
            logger.warning("Failed to write trace log: %s", exc)

    def _load_memory(self) -> None:
        """Load execution memory from disk."""
        if not os.path.exists(self._memory_file):
            return

        try:
            with open(self._memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._memory.total_cycles = data.get("total_cycles", 0)
            self._memory.total_blocks_processed = data.get("total_blocks_processed", 0)
            self._memory.total_retries = data.get("total_retries", 0)
            self._memory.total_rollbacks = data.get("total_rollbacks", 0)
            self._memory.last_cycle_timestamp = data.get("last_cycle_timestamp", "")
            self._memory.failure_patterns = data.get("failure_patterns", {})

            # Restore recent traces
            for trace_data in data.get("recent_traces", []):
                entry = TraceEntry(
                    block_id=trace_data.get("block_id", ""),
                    block_title=trace_data.get("block_title", ""),
                    attempt=trace_data.get("attempt", 1),
                    timestamp=trace_data.get("timestamp", ""),
                    action=trace_data.get("action", ""),
                    handler_type=trace_data.get("handler_type", ""),
                    input_summary=trace_data.get("input_summary", ""),
                    output_summary=trace_data.get("output_summary", ""),
                    status=trace_data.get("status", ""),
                    duration_ms=trace_data.get("duration_ms", 0),
                    error=trace_data.get("error", ""),
                    files_affected=trace_data.get("files_affected", []),
                    rollback_available=trace_data.get("rollback_available", False),
                )
                self._memory.traces.append(entry)

        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load memory file: %s. Starting fresh.", exc)
            self._memory = ExecutionMemory()

    def _save_memory(self) -> None:
        """Persist execution memory to disk."""
        Path(os.path.dirname(self._memory_file)).mkdir(parents=True, exist_ok=True)

        # Serialize recent traces (keep last N)
        recent_traces = self._memory.traces[-MAX_TRACE_ENTRIES:]
        trace_dicts = []
        for entry in recent_traces:
            trace_dicts.append({
                "block_id": entry.block_id,
                "block_title": entry.block_title,
                "attempt": entry.attempt,
                "timestamp": entry.timestamp,
                "action": entry.action,
                "handler_type": entry.handler_type,
                "input_summary": entry.input_summary,
                "output_summary": entry.output_summary,
                "status": entry.status,
                "duration_ms": entry.duration_ms,
                "error": entry.error,
                "files_affected": entry.files_affected,
                "rollback_available": entry.rollback_available,
            })

        data = {
            "total_cycles": self._memory.total_cycles,
            "total_blocks_processed": self._memory.total_blocks_processed,
            "total_retries": self._memory.total_retries,
            "total_rollbacks": self._memory.total_rollbacks,
            "last_cycle_timestamp": self._memory.last_cycle_timestamp,
            "failure_patterns": self._memory.failure_patterns,
            "recent_traces": trace_dicts,
        }

        try:
            content = json.dumps(data, indent=2)
            # Enforce max file size
            if len(content.encode("utf-8")) > MAX_MEMORY_FILE_SIZE:
                # Trim older traces
                half = len(trace_dicts) // 2
                data["recent_traces"] = trace_dicts[half:]
                content = json.dumps(data, indent=2)

            Path(self._memory_file).write_text(content, encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to save memory file: %s", exc)

    def _prune_memory(self) -> None:
        """Prune old trace entries to stay within limits."""
        if len(self._memory.traces) > MAX_TRACE_ENTRIES:
            self._memory.traces = self._memory.traces[-MAX_TRACE_ENTRIES:]
