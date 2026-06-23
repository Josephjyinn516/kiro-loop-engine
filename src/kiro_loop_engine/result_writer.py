"""Result Writer for the Kiro Loop Engine.

Writes execution results back into the control file as H3 sub-sections
and updates instruction block status fields.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from kiro_loop_engine.constants import MAX_OUTPUT_LENGTH, MAX_SUMMARY_LENGTH
from kiro_loop_engine.models import InstructionBlock, ResultBlock


class ResultWriter:
    """Writes execution results back into the control file."""

    RETRY_DELAY_SECONDS: float = 1.0

    def write_result(
        self,
        file_content: str,
        block: InstructionBlock,
        result: ResultBlock,
    ) -> str:
        """Return updated file content with the result block inserted/replaced."""
        lines = file_content.split("\n")

        lines = self._update_status_field(lines, block, result.status)

        result_start, result_end = self._find_existing_result_block(
            lines, block.raw_start_line, block.raw_end_line
        )

        formatted_result = self._format_result_block(result)

        if result_start is not None and result_end is not None:
            lines[result_start:result_end] = formatted_result.split("\n")
        else:
            insert_at = block.raw_end_line
            result_lines = formatted_result.split("\n")
            lines[insert_at:insert_at] = [""] + result_lines

        return "\n".join(lines)

    def _update_status_field(
        self, lines: list[str], block: InstructionBlock, new_status: str
    ) -> list[str]:
        status_pattern = re.compile(r"^status:\s*.+$")
        search_end = min(block.raw_start_line + 10, block.raw_end_line)

        for i in range(block.raw_start_line, search_end):
            if i < len(lines) and status_pattern.match(lines[i]):
                lines[i] = f"status: {new_status}"
                break

        return lines

    def _find_existing_result_block(
        self, lines: list[str], block_start: int, block_end: int
    ) -> tuple[int | None, int | None]:
        result_heading_pattern = re.compile(r"^###\s+Result\s*$")
        result_start = None

        for i in range(block_start, min(block_end, len(lines))):
            if result_heading_pattern.match(lines[i]):
                result_start = i
                break

        if result_start is None:
            return (None, None)

        result_end = min(block_end, len(lines))
        for i in range(result_start + 1, min(block_end, len(lines))):
            if re.match(r"^#{1,3}\s+", lines[i]):
                result_end = i
                break

        return (result_start, result_end)

    def _format_result_block(self, result: ResultBlock) -> str:
        summary, summary_truncated = self._truncate(result.summary, MAX_SUMMARY_LENGTH)
        output, output_truncated = self._truncate(result.output, MAX_OUTPUT_LENGTH)

        lines = [
            "### Result",
            "",
            f"timestamp: {result.timestamp}",
            f"status: {result.status}",
            f"summary: {summary}{'[truncated]' if summary_truncated else ''}",
        ]

        if output:
            if "\n" in output or output_truncated:
                lines.append("output: |")
                for output_line in output.split("\n"):
                    lines.append(f"  {output_line}")
                if output_truncated:
                    lines.append("  [truncated]")
            else:
                lines.append(f"output: {output}")

        return "\n".join(lines)

    def _truncate(self, text: str, max_length: int) -> tuple[str, bool]:
        if len(text) <= max_length:
            return (text, False)
        return (text[:max_length], True)

    def save(self, path: str, content: str) -> bool:
        """Write content to file with a single retry on failure."""
        for attempt in range(2):
            try:
                Path(path).write_text(content, encoding="utf-8")
                return True
            except OSError:
                if attempt == 0:
                    time.sleep(self.RETRY_DELAY_SECONDS)
        return False
