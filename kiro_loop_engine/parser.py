"""Parser for the loop engineering control file.

Extracts InstructionBlocks from H2-delimited markdown sections,
including metadata, descriptions, file path references, and existing
Result_Blocks.
"""

from __future__ import annotations

import hashlib
import re

from kiro_loop_engine.constants import VALID_PRIORITIES, VALID_STATUSES, VALID_TYPES
from kiro_loop_engine.models import InstructionBlock, ResultBlock


# Recognized metadata keys in instruction blocks
_METADATA_KEYS = {"type", "status", "priority", "safety", "max-retries", "verify", "accept"}

# Pattern to match file paths in content
_FILE_PATH_PATTERN = re.compile(
    r"(?:^|\s)([a-zA-Z0-9_.][a-zA-Z0-9_./\\-]*\.[a-zA-Z0-9]{1,10})(?:\s|$|[,;)\]])",
    re.MULTILINE,
)


class Parser:
    """Parses the control file into structured instruction blocks."""

    def parse(self, content: str) -> list[InstructionBlock]:
        """Parse markdown content into an InstructionBlock list.

        Splits content by H2 headings (``## ``). Each H2 section becomes
        one InstructionBlock with metadata extracted from key-value lines
        immediately following the heading, and description from the remaining
        body text.

        An empty file (or file with no H2 headings) returns an empty list.
        """
        if not content or not content.strip():
            return []

        lines = content.split("\n")
        blocks: list[InstructionBlock] = []

        # Find all H2 heading positions
        h2_indices: list[int] = []
        for i, line in enumerate(lines):
            if line.startswith("## "):
                h2_indices.append(i)

        if not h2_indices:
            return []

        # Process each H2 section
        for idx, start in enumerate(h2_indices):
            if idx + 1 < len(h2_indices):
                end = h2_indices[idx + 1] - 1
            else:
                end = len(lines) - 1

            # Strip trailing empty lines from block end
            while end > start and not lines[end].strip():
                end -= 1

            block = self._parse_block(lines, start, end)
            blocks.append(block)

        return blocks

    def _parse_block(self, lines: list[str], start: int, end: int) -> InstructionBlock:
        """Parse a single H2 section into an InstructionBlock."""
        title = lines[start][3:].strip()

        metadata_lines: list[str] = []
        body_start = start + 1

        if body_start <= end and not lines[body_start].strip():
            body_start += 1

        i = body_start
        while i <= end:
            line = lines[i].strip()
            if not line:
                i += 1
                break
            if self._is_metadata_line(line):
                metadata_lines.append(line)
                i += 1
            else:
                break
        body_start = i

        metadata = self._extract_metadata(metadata_lines)

        result_block = None
        description_end = end
        for j in range(body_start, end + 1):
            if lines[j].strip().lower().startswith("### result"):
                description_end = j - 1
                result_block = self._parse_result_block(lines, j, end)
                break

        description_lines = lines[body_start : description_end + 1]
        description = "\n".join(description_lines).strip()

        # Extract file paths from description only (not metadata/verify lines)
        file_paths = self._extract_file_paths(description)

        block_type = metadata.get("type", "")
        status = metadata.get("status", "pending")
        priority = metadata.get("priority", "normal")
        safety = metadata.get("safety", "")
        max_retries_str = metadata.get("max-retries", "3")
        verify = metadata.get("verify", "")
        accept = metadata.get("accept", "")

        # Parse max-retries safely
        try:
            max_retries = int(max_retries_str)
        except (ValueError, TypeError):
            max_retries = 3

        block_id = self._generate_id(title, start)

        return InstructionBlock(
            id=block_id,
            type=block_type,
            title=title,
            description=description,
            priority=priority,
            status=status,
            file_paths=file_paths,
            safety_confirmed=(safety.lower() == "confirmed"),
            raw_start_line=start,
            raw_end_line=end,
            result_block=result_block,
            max_retries=max_retries,
            verify=verify,
            acceptance_criteria=accept,
        )

    def _is_metadata_line(self, line: str) -> bool:
        """Check if a line matches the key: value metadata format."""
        if ":" not in line:
            return False
        key = line.split(":", 1)[0].strip().lower()
        return key in _METADATA_KEYS

    def _extract_metadata(self, lines: list[str]) -> dict[str, str]:
        """Extract key: value metadata from lines following an H2 heading."""
        metadata: dict[str, str] = {}
        for line in lines:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if key in _METADATA_KEYS:
                metadata[key] = value
        return metadata

    def _extract_file_paths(self, content: str) -> list[str]:
        """Find explicit file path references in block content."""
        matches = _FILE_PATH_PATTERN.findall(content)
        seen: set[str] = set()
        paths: list[str] = []
        for match in matches:
            if match.startswith("##") or match.startswith("#"):
                continue
            if (
                "/" in match
                or "\\" in match
                or match.startswith(".")
                or re.match(r"^[a-zA-Z0-9_-]+\.[a-zA-Z]{1,10}$", match)
            ):
                if match not in seen:
                    seen.add(match)
                    paths.append(match)
        return paths

    def _parse_result_block(self, lines: list[str], start: int, end: int) -> ResultBlock:
        """Parse an existing ### Result section into a ResultBlock."""
        result_lines = lines[start + 1 : end + 1]
        timestamp = ""
        status = ""
        summary = ""
        output_lines: list[str] = []
        in_output = False

        for line in result_lines:
            stripped = line.strip()
            if not stripped:
                if in_output:
                    output_lines.append("")
                continue

            if not in_output:
                if stripped.startswith("timestamp:"):
                    timestamp = stripped[len("timestamp:"):].strip()
                elif stripped.startswith("status:"):
                    status = stripped[len("status:"):].strip()
                elif stripped.startswith("summary:"):
                    summary = stripped[len("summary:"):].strip()
                elif stripped.startswith("output:"):
                    output_value = stripped[len("output:"):].strip()
                    if output_value and output_value != "|":
                        output_lines.append(output_value)
                    in_output = True
                else:
                    if output_lines or in_output:
                        output_lines.append(stripped)
            else:
                if line.startswith("  "):
                    output_lines.append(line[2:])
                else:
                    output_lines.append(line)

        output = "\n".join(output_lines).strip()
        truncated = "[truncated]" in output

        return ResultBlock(
            timestamp=timestamp,
            status=status,
            summary=summary,
            output=output,
            truncated=truncated,
        )

    def validate_block(self, block: InstructionBlock) -> list[str]:
        """Return list of validation errors (empty if valid)."""
        errors: list[str] = []

        if not block.title or not block.title.strip():
            errors.append("Missing required field: title")

        if not block.type or not block.type.strip():
            errors.append("Missing required field: type")
        elif block.type not in VALID_TYPES:
            errors.append(
                f"Unrecognized type '{block.type}'. "
                f"Supported types: {', '.join(VALID_TYPES)}"
            )

        return errors

    def _generate_id(self, title: str, start_line: int) -> str:
        """Generate a deterministic unique ID for a block."""
        raw = f"{title}:{start_line}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]
