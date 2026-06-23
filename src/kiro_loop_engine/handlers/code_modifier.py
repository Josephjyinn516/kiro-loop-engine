"""Code Modifier handler for change-request type instruction blocks."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from kiro_loop_engine.handlers.base import BaseHandler
from kiro_loop_engine.models import InstructionBlock, ResultBlock


class CodeModifierHandler(BaseHandler):
    """Handles type=change-request blocks by modifying existing files atomically."""

    def __init__(self, project_root: str) -> None:
        self.project_root = project_root

    def execute(self, block: InstructionBlock) -> ResultBlock:
        target_files = self._identify_targets(block)

        if not target_files:
            return self._make_result(
                status="failed",
                summary="No target files identified for change request.",
                output="Please specify target file paths explicitly.",
            )

        missing_files = self._check_files_exist(target_files)
        if missing_files:
            return self._make_result(
                status="failed",
                summary=f"Atomicity check failed: {len(missing_files)} file(s) missing.",
                output=f"Missing: {', '.join(missing_files)}. No files were modified.",
            )

        change_summaries: list[str] = []
        failed_regions: list[str] = []

        for file_path in target_files:
            resolved_path = self._resolve_path(file_path)
            try:
                content = self._read_file(resolved_path)
            except OSError as exc:
                return self._make_result(
                    status="failed",
                    summary=f"Failed to read target file: {file_path}",
                    output=str(exc),
                )

            region_info = self._find_code_region(content, block.description, file_path)
            if region_info is None:
                failed_regions.append(file_path)
                continue

            modified_content, change_description = self._apply_modification(
                content, region_info, block.description
            )

            try:
                self._write_file(resolved_path, modified_content)
                change_summaries.append(f"- {file_path}: {change_description}")
            except OSError as exc:
                return self._make_result(
                    status="failed",
                    summary=f"Failed to write modified file: {file_path}",
                    output=str(exc),
                )

        if failed_regions:
            return self._make_result(
                status="failed",
                summary=f"Code region not found in {len(failed_regions)} file(s).",
                output=f"Could not locate pattern in: {', '.join(failed_regions)}.",
            )

        return self._make_result(
            status="completed",
            summary=f"Modified {len(change_summaries)} file(s) successfully.",
            output="\n".join(change_summaries),
        )

    def _identify_targets(self, block: InstructionBlock) -> list[str]:
        if block.file_paths:
            return list(block.file_paths)
        if block.description:
            return self._infer_paths_from_description(block.description)
        return []

    def _infer_paths_from_description(self, description: str) -> list[str]:
        paths: list[str] = []
        backtick_pattern = r"`([^`]+\.[a-zA-Z0-9]+)`"
        for match in re.findall(backtick_pattern, description):
            if self._looks_like_path(match):
                paths.append(match)
        bare_path_pattern = r"(?:^|\s)((?:\.?/)?(?:[\w\-./\\]+\.(?:py|js|ts|jsx|tsx|css|html|json|yaml|yml|toml|md|txt|sql|sh|bat|ps1|cfg|ini|xml)))"
        for match in re.findall(bare_path_pattern, description, re.MULTILINE):
            if match not in paths and self._looks_like_path(match):
                paths.append(match)
        return paths

    def _looks_like_path(self, text: str) -> bool:
        if "." not in text:
            return False
        if text.startswith("http://") or text.startswith("https://"):
            return False
        if " " in text and "\\ " not in text:
            return False
        return True

    def _check_files_exist(self, file_paths: list[str]) -> list[str]:
        missing: list[str] = []
        for file_path in file_paths:
            resolved = self._resolve_path(file_path)
            if not os.path.isfile(resolved):
                missing.append(file_path)
        return missing

    def _resolve_path(self, file_path: str) -> str:
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(self.project_root, file_path)

    def _find_code_region(self, content: str, description: str, file_path: str) -> dict | None:
        if not description:
            return None

        code_patterns = re.findall(r"`([^`]+)`", description)
        for pattern in code_patterns:
            if self._looks_like_path(pattern):
                continue
            if pattern in content:
                start_idx = content.index(pattern)
                start_line = content[:start_idx].count("\n")
                end_line = start_line + pattern.count("\n")
                return {"start_line": start_line, "end_line": end_line, "matched_text": pattern}

        name_patterns = [
            r"(?:function|def|class|method)\s+(\w+)",
            r"rename\s+(\w+)",
            r"modify\s+(\w+)",
            r"update\s+(\w+)",
            r"change\s+(\w+)",
        ]
        for name_pattern in name_patterns:
            matches = re.findall(name_pattern, description, re.IGNORECASE)
            for name in matches:
                symbol_patterns = [
                    rf"\bdef\s+{re.escape(name)}\b",
                    rf"\bclass\s+{re.escape(name)}\b",
                    rf"\bfunction\s+{re.escape(name)}\b",
                    rf"\b{re.escape(name)}\s*[=(]",
                ]
                for sym_pattern in symbol_patterns:
                    match = re.search(sym_pattern, content)
                    if match:
                        start_idx = match.start()
                        start_line = content[:start_idx].count("\n")
                        return {"start_line": start_line, "end_line": start_line, "matched_text": match.group(0)}

        return None

    def _apply_modification(self, content: str, region_info: dict, description: str) -> tuple[str, str]:
        matched_text = region_info["matched_text"]
        start_line = region_info["start_line"]

        replacement = self._extract_replacement(description, matched_text)
        if replacement is not None and replacement != matched_text:
            modified_content = content.replace(matched_text, replacement, 1)
            change_description = f"Replaced at line {start_line + 1}: '{matched_text[:50]}' -> '{replacement[:50]}'"
        else:
            modified_content = content
            change_description = f"Identified region at line {start_line + 1}: '{matched_text[:80]}'"

        return modified_content, change_description

    def _extract_replacement(self, description: str, matched_text: str) -> str | None:
        replace_patterns = [
            r"replace\s+[`'\"]?(.+?)[`'\"]?\s+with\s+[`'\"]?(.+?)[`'\"]?(?:\s|$|\.)",
            r"change\s+[`'\"]?(.+?)[`'\"]?\s+to\s+[`'\"]?(.+?)[`'\"]?(?:\s|$|\.)",
            r"rename\s+[`'\"]?(.+?)[`'\"]?\s+to\s+[`'\"]?(.+?)[`'\"]?(?:\s|$|\.)",
        ]
        for pattern in replace_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                old_text = match.group(1).strip()
                new_text = match.group(2).strip()
                if old_text in matched_text or matched_text in old_text:
                    return matched_text.replace(old_text, new_text)
                return new_text
        return None

    def _read_file(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_file(self, path: str, content: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _make_result(self, status: str, summary: str, output: str) -> ResultBlock:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        truncated = False
        if len(summary) > 500:
            summary = summary[:497] + "..."
            truncated = True
        if len(output) > 2000:
            output = output[:1997] + "..."
            truncated = True
        return ResultBlock(timestamp=timestamp, status=status, summary=summary, output=output, truncated=truncated)
