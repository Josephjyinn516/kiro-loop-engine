"""TestRunnerHandler for the Kiro Loop Engine."""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from enum import Enum

from kiro_loop_engine.constants import TEST_TIMEOUT_SECONDS
from kiro_loop_engine.handlers.base import BaseHandler
from kiro_loop_engine.models import InstructionBlock, ResultBlock


class TestMode(Enum):
    FILE = "file"
    COMMAND = "command"
    BEHAVIOR = "behavior"


class TestRunnerHandler(BaseHandler):
    """Handles type=test instruction blocks."""

    _COMMAND_PATTERNS: list[str] = [
        r"^\s*(?:pytest|python|npm|npx|node|yarn|pnpm|cargo|go|dotnet|mvn|gradle)\s+",
        r"^\s*(?:make|bash|sh|cmd|powershell|pwsh)\s+",
        r"^\s*\$\s+",
    ]

    _PASS_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"(\d+)\s+passed", re.IGNORECASE),
        re.compile(r"passed[:\s]+(\d+)", re.IGNORECASE),
        re.compile(r"Tests:\s*(\d+)\s+passed", re.IGNORECASE),
        re.compile(r"OK\s*\((\d+)\s+test", re.IGNORECASE),
    ]

    _FAIL_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"(\d+)\s+failed", re.IGNORECASE),
        re.compile(r"failed[:\s]+(\d+)", re.IGNORECASE),
        re.compile(r"Tests:\s*(\d+)\s+failed", re.IGNORECASE),
        re.compile(r"FAILED\s*\(.*?failures=(\d+)", re.IGNORECASE),
        re.compile(r"(\d+)\s+error", re.IGNORECASE),
    ]

    def __init__(self, project_root: str, timeout: int = TEST_TIMEOUT_SECONDS) -> None:
        self.project_root = project_root
        self.timeout = timeout

    def execute(self, block: InstructionBlock) -> ResultBlock:
        mode = self._determine_mode(block)
        if mode == TestMode.FILE:
            return self._run_test_file(block)
        elif mode == TestMode.COMMAND:
            return self._run_command(block)
        else:
            return self._validate_behavior(block)

    def _determine_mode(self, block: InstructionBlock) -> TestMode:
        if block.file_paths:
            return TestMode.FILE
        if block.description:
            for line in block.description.strip().splitlines():
                stripped = line.strip()
                for pattern in self._COMMAND_PATTERNS:
                    if re.match(pattern, stripped, re.IGNORECASE):
                        return TestMode.COMMAND
        return TestMode.BEHAVIOR

    def _run_test_file(self, block: InstructionBlock) -> ResultBlock:
        missing_files: list[str] = []
        resolved_paths: list[str] = []

        for file_path in block.file_paths:
            full_path = file_path if os.path.isabs(file_path) else os.path.join(self.project_root, file_path)
            resolved = os.path.realpath(full_path)
            if not os.path.isfile(resolved):
                missing_files.append(file_path)
            else:
                resolved_paths.append(resolved)

        if missing_files:
            return self._make_result(
                status="failed",
                summary=f"Test file(s) not found: {', '.join(missing_files)}",
                output=f"Missing: {', '.join(missing_files)}",
            )

        command = ["python", "-m", "pytest"] + resolved_paths + ["-v"]
        return self._execute_subprocess(command)

    def _run_command(self, block: InstructionBlock) -> ResultBlock:
        command_str = self._extract_command(block.description)
        if not command_str:
            return self._make_result(status="failed", summary="No command found.", output="")
        return self._execute_subprocess(command_str, shell=True)

    def _validate_behavior(self, block: InstructionBlock) -> ResultBlock:
        description = block.description.strip() if block.description else ""
        if not description:
            return self._make_result(status="failed", summary="No behavior description.", output="")
        return self._make_result(
            status="completed",
            summary="Behavior validation request recorded.",
            output=f"Behavior: {description[:500]}",
        )

    def _execute_subprocess(self, command: list[str] | str, shell: bool = False) -> ResultBlock:
        try:
            result = subprocess.run(
                command, capture_output=True, text=True,
                timeout=self.timeout, cwd=self.project_root, shell=shell,
            )
            combined_output = result.stdout + ("\n" + result.stderr if result.stderr else "")
            pass_count = self._extract_count(combined_output, self._PASS_PATTERNS)
            fail_count = self._extract_count(combined_output, self._FAIL_PATTERNS)

            if result.returncode == 0:
                return self._make_result(
                    status="completed",
                    summary=f"Tests passed. Pass: {pass_count}, Fail: {fail_count}.",
                    output=combined_output,
                )
            else:
                is_infra = self._is_infrastructure_error(result.returncode, combined_output)
                if is_infra:
                    return self._make_result(status="failed", summary="Infrastructure error.", output=combined_output)
                else:
                    return self._make_result(
                        status="completed",
                        summary=f"Tests with failures. Pass: {pass_count}, Fail: {fail_count}.",
                        output=combined_output,
                    )
        except subprocess.TimeoutExpired:
            return self._make_result(status="failed", summary=f"Timed out after {self.timeout}s.", output="")
        except FileNotFoundError as exc:
            return self._make_result(status="failed", summary="Command not found.", output=str(exc))
        except OSError as exc:
            return self._make_result(status="failed", summary="Execution error.", output=str(exc))

    def _extract_command(self, description: str) -> str:
        if not description:
            return ""
        for line in description.strip().splitlines():
            stripped = line.strip()
            if stripped.startswith("$ "):
                return stripped[2:].strip()
            for pattern in self._COMMAND_PATTERNS:
                if re.match(pattern, stripped, re.IGNORECASE):
                    return stripped
        return ""

    def _extract_count(self, output: str, patterns: list[re.Pattern[str]]) -> int:
        for pattern in patterns:
            match = pattern.search(output)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        return 0

    def _is_infrastructure_error(self, returncode: int, output: str) -> bool:
        infra_indicators = ["ModuleNotFoundError", "ImportError", "SyntaxError", "FileNotFoundError", "No module named", "command not found"]
        assertion_indicators = ["AssertionError", "FAILED", "failed", "passed", "assert "]
        output_lower = output.lower()
        for ind in assertion_indicators:
            if ind.lower() in output_lower:
                return False
        for ind in infra_indicators:
            if ind in output:
                return True
        if returncode >= 2:
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
        return ResultBlock(timestamp=timestamp, status=status, summary=summary, output=output, truncated=truncated)
