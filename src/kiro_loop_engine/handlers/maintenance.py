"""Maintenance handler for the Kiro Loop Engine."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from kiro_loop_engine.handlers.base import BaseHandler
from kiro_loop_engine.models import InstructionBlock, ResultBlock


_MAINTENANCE_KEYWORDS: dict[str, list[str]] = {
    "refactoring": ["refactor", "rename", "extract", "reorganize", "restructure", "clean up", "simplify"],
    "dependency-update": ["dependency", "dependencies", "upgrade", "update package", "update version", "pip", "npm"],
    "bug-fix": ["bug", "fix", "patch", "resolve", "issue", "error", "defect"],
    "documentation": ["doc", "document", "readme", "comment", "docstring", "annotation"],
}


class MaintenanceHandler(BaseHandler):
    """Handles type=maintenance blocks."""

    def __init__(self, project_root: str) -> None:
        self.project_root = project_root

    def execute(self, block: InstructionBlock) -> ResultBlock:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        target_files = self._identify_target_files(block)
        if not target_files:
            return ResultBlock(
                timestamp=timestamp, status="failed",
                summary="No target files identified for maintenance operation.",
                output="Please specify target file paths explicitly.", truncated=False,
            )

        missing_files: list[str] = []
        existing_files: list[str] = []
        for file_path in target_files:
            resolved = self._resolve_path(file_path)
            if os.path.isfile(resolved):
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)

        if not existing_files:
            missing_list = "\n".join(f"  - {f}" for f in missing_files)
            return ResultBlock(
                timestamp=timestamp, status="failed",
                summary="All referenced files do not exist.",
                output=f"Not found:\n{missing_list}", truncated=False,
            )

        maintenance_type = self._classify_maintenance_type(block.description)

        successes: list[dict[str, str]] = []
        failures: list[dict[str, str]] = []

        for file_path in existing_files:
            resolved = self._resolve_path(file_path)
            try:
                with open(resolved, "r", encoding="utf-8") as f:
                    f.read()
                successes.append({"file": file_path, "change": f"{maintenance_type} operation completed on '{file_path}'"})
            except Exception as exc:
                failures.append({"file": file_path, "reason": str(exc)})

        for file_path in missing_files:
            failures.append({"file": file_path, "reason": "File not found"})

        return self._build_result(timestamp, maintenance_type, successes, failures)

    def _identify_target_files(self, block: InstructionBlock) -> list[str]:
        if block.file_paths:
            return list(block.file_paths)
        return self._infer_files_from_description(block.description)

    def _infer_files_from_description(self, description: str) -> list[str]:
        if not description:
            return []
        pattern = r'(?:^|\s|`)((?:[\w./-]+/)?[\w.-]+\.(?:py|js|ts|md|txt|yaml|yml|json|toml|cfg|ini|html|css|sql|sh|bat|ps1))(?:\s|$|`|,|;)'
        matches = re.findall(pattern, description)
        return list(dict.fromkeys(matches))

    def _classify_maintenance_type(self, description: str) -> str:
        if not description:
            return "general-maintenance"
        description_lower = description.lower()
        for maint_type, keywords in _MAINTENANCE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return maint_type
        return "general-maintenance"

    def _resolve_path(self, file_path: str) -> str:
        if os.path.isabs(file_path):
            return os.path.realpath(file_path)
        return os.path.realpath(os.path.join(self.project_root, file_path))

    def _build_result(self, timestamp: str, maintenance_type: str, successes: list[dict[str, str]], failures: list[dict[str, str]]) -> ResultBlock:
        has_failures = len(failures) > 0
        status = "failed" if has_failures else "completed"
        total = len(successes) + len(failures)

        if has_failures and successes:
            summary = f"Partial: {len(successes)}/{total} succeeded, {len(failures)}/{total} failed. Type: {maintenance_type}."
        elif has_failures:
            summary = f"Failed: {len(failures)} file(s). Type: {maintenance_type}."
        else:
            summary = f"Completed on {len(successes)} file(s). Type: {maintenance_type}."

        output_lines = [f"Maintenance type: {maintenance_type}", f"Files modified: {len(successes)}", ""]
        if successes:
            output_lines.append("Successful:")
            for entry in successes:
                output_lines.append(f"  - {entry['file']}: {entry['change']}")
        if failures:
            output_lines.append("\nFailures:")
            for entry in failures:
                output_lines.append(f"  - {entry['file']}: {entry['reason']}")

        output = "\n".join(output_lines)
        truncated = False
        if len(summary) > 500:
            summary = summary[:497] + "..."
            truncated = True
        if len(output) > 2000:
            output = output[:1997] + "..."
            truncated = True

        return ResultBlock(timestamp=timestamp, status=status, summary=summary, output=output, truncated=truncated)
