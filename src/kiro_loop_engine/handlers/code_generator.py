"""Code Generator handler for type=task instruction blocks."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from kiro_loop_engine.handlers.base import BaseHandler
from kiro_loop_engine.models import InstructionBlock, ResultBlock
from kiro_loop_engine.safety import validate_paths


class CodeGeneratorHandler(BaseHandler):
    """Handles type=task blocks by generating new code files."""

    OVERWRITE_KEYWORDS: list[str] = ["overwrite", "replace", "update", "rewrite"]

    def __init__(self, project_root: str) -> None:
        self.project_root = project_root

    def execute(self, block: InstructionBlock) -> ResultBlock:
        target_paths = self._resolve_target_paths(block)

        if not target_paths:
            return self._make_result(
                status="failed",
                summary="No target file paths could be determined from the instruction.",
                output="Please provide target file paths in the instruction block.",
            )

        outside_paths = validate_paths(target_paths, self.project_root)
        if outside_paths:
            return self._make_result(
                status="failed",
                summary="Path validation failed: paths outside project boundary.",
                output=f"Outside boundary: {', '.join(outside_paths)}",
            )

        has_overwrite_intent = self._has_overwrite_intent(block)
        conflicts = self._detect_conflicts(target_paths, has_overwrite_intent)
        if conflicts:
            return self._make_result(
                status="failed",
                summary="File conflict detected: target file(s) already exist.",
                output=f"Existing: {', '.join(conflicts)}. Add overwrite intent to proceed.",
            )

        created_files: list[str] = []
        errors: list[str] = []

        for target_path in target_paths:
            try:
                self._generate_file(target_path, block)
                rel_path = os.path.relpath(
                    os.path.join(self.project_root, target_path)
                    if not os.path.isabs(target_path)
                    else target_path,
                    self.project_root,
                )
                created_files.append(rel_path)
            except OSError as exc:
                errors.append(f"{target_path}: {exc}")

        if errors and not created_files:
            return self._make_result(
                status="failed",
                summary=f"Code generation failed for all {len(errors)} file(s).",
                output="Errors:\n" + "\n".join(f"  - {e}" for e in errors),
            )

        if errors:
            output_lines = [f"Created {len(created_files)} file(s):"]
            output_lines.extend(f"  - {f}" for f in created_files)
            output_lines.append(f"\nFailed {len(errors)} file(s):")
            output_lines.extend(f"  - {e}" for e in errors)
            return self._make_result(
                status="failed",
                summary=f"Partial: {len(created_files)} created, {len(errors)} failed.",
                output="\n".join(output_lines),
            )

        output_lines = [f"Created {len(created_files)} file(s):"]
        output_lines.extend(f"  - {f}" for f in created_files)
        return self._make_result(
            status="completed",
            summary=f"Successfully created {len(created_files)} file(s).",
            output="\n".join(output_lines),
        )

    def _resolve_target_paths(self, block: InstructionBlock) -> list[str]:
        if block.file_paths:
            return list(block.file_paths)
        return self._infer_paths_from_description(block.description)

    def _infer_paths_from_description(self, description: str) -> list[str]:
        if not description:
            return []
        path_pattern = r'(?:^|\s|`|"|\')([a-zA-Z0-9_./\\-]+(?:/|\\\\)[a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)'
        matches = re.findall(path_pattern, description)
        simple_file_pattern = r'(?:^|\s|`|"|\')([a-zA-Z_][a-zA-Z0-9_]*\.(?:py|js|ts|java|rb|go|rs|c|h|cpp|hpp|css|html|json|yaml|yml|toml|md))'
        simple_matches = re.findall(simple_file_pattern, description)
        all_paths: list[str] = []
        seen: set[str] = set()
        for path in matches + simple_matches:
            normalized = path.replace("\\\\", "/").replace("\\", "/")
            if normalized not in seen:
                seen.add(normalized)
                all_paths.append(normalized)
        return all_paths

    def _has_overwrite_intent(self, block: InstructionBlock) -> bool:
        text = f"{block.title} {block.description}".lower()
        return any(keyword in text for keyword in self.OVERWRITE_KEYWORDS)

    def _detect_conflicts(self, paths: list[str], has_overwrite_intent: bool) -> list[str]:
        if has_overwrite_intent:
            return []
        conflicts: list[str] = []
        for path in paths:
            full_path = (
                os.path.join(self.project_root, path) if not os.path.isabs(path) else path
            )
            if os.path.exists(full_path):
                conflicts.append(path)
        return conflicts

    def _generate_file(self, target_path: str, block: InstructionBlock) -> None:
        full_path = (
            os.path.join(self.project_root, target_path)
            if not os.path.isabs(target_path)
            else target_path
        )
        parent_dir = os.path.dirname(full_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        content = self._generate_content(target_path, block)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _generate_content(self, target_path: str, block: InstructionBlock) -> str:
        ext = os.path.splitext(target_path)[1].lower()
        module_name = os.path.splitext(os.path.basename(target_path))[0]
        description = block.description.strip() if block.description else block.title

        if ext == ".py":
            docstring = description.split("\n")[0][:80]
            return f'"""{docstring}\n\nGenerated by Kiro Loop Engine.\n"""\n\n\n# TODO: Implement {module_name}\n'
        elif ext in (".js", ".ts"):
            comment = description.split("\n")[0][:80]
            return f"/**\n * {comment}\n *\n * Generated by Kiro Loop Engine.\n */\n\n// TODO: Implement {module_name}\n"
        elif ext == ".json":
            return "{\n" f'  "_comment": "Generated by Kiro Loop Engine: {module_name}"\n' "}\n"
        elif ext in (".yaml", ".yml"):
            comment = description.split("\n")[0][:60]
            return f"# {comment}\n# Generated by Kiro Loop Engine.\n"
        elif ext == ".md":
            title = module_name.replace("_", " ").replace("-", " ").title()
            return f"# {title}\n\n{description}\n"
        else:
            comment = description.split("\n")[0][:80]
            return f"# {comment}\n# Generated by Kiro Loop Engine.\n"

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
