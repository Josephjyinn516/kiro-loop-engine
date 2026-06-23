"""Safety guardrails for the Kiro Loop Engine.

Provides path boundary enforcement, destructive command detection,
and timeout enforcement utilities.
"""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Callable

from kiro_loop_engine.constants import DESTRUCTIVE_PATTERNS


def validate_paths(paths: list[str], project_root: str) -> list[str]:
    """Validate that all paths resolve within the project root directory.

    Resolves each path to its absolute real path (following symlinks and
    normalizing traversal sequences like ``../``). Relative paths are resolved
    relative to *project_root*.

    Args:
        paths: List of file paths (relative or absolute) to validate.
        project_root: The project root directory that defines the allowed boundary.

    Returns:
        A list of paths that are OUTSIDE the project boundary. An empty list
        means all paths are valid.
    """
    resolved_root = os.path.realpath(project_root)
    if not resolved_root.endswith(os.sep):
        root_prefix = resolved_root + os.sep
    else:
        root_prefix = resolved_root

    outside_paths: list[str] = []
    for path in paths:
        if not os.path.isabs(path):
            full_path = os.path.join(resolved_root, path)
        else:
            full_path = path

        resolved = os.path.realpath(full_path)

        if resolved != resolved_root and not resolved.startswith(root_prefix):
            outside_paths.append(path)

    return outside_paths


def is_destructive(command: str) -> bool:
    """Check if a shell command matches known destructive patterns.

    Args:
        command: The shell command string to check.

    Returns:
        True if ANY destructive pattern matches the command, False otherwise.
    """
    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False


def enforce_timeout(func: Callable[..., Any], timeout: int, *args: Any, **kwargs: Any) -> Any:
    """Execute a function with a timeout, raising TimeoutError if exceeded.

    Args:
        func: The callable to execute.
        timeout: Maximum number of seconds to wait for the function to complete.
        *args: Positional arguments to pass to *func*.
        **kwargs: Keyword arguments to pass to *func*.

    Returns:
        The return value of *func*.

    Raises:
        TimeoutError: If the function does not complete within *timeout* seconds.
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            raise TimeoutError(
                f"Function {func.__name__!r} exceeded timeout of {timeout} seconds"
            )
