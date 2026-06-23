"""Constants for the Kiro Loop Engine.

Implements the full Loop Engineering architecture constants including
verification loop, hill-climbing, and guardrail parameters.
"""

# Valid instruction block types
VALID_TYPES: list[str] = ["task", "change-request", "test", "maintenance"]

# Valid instruction block statuses
VALID_STATUSES: list[str] = [
    "pending",
    "in-progress",
    "completed",
    "failed",
    "skipped",
    "retrying",
    "needs-verification",
    "escalated",
]

# Valid priority levels
VALID_PRIORITIES: list[str] = ["low", "normal", "high"]

# Shell command patterns considered destructive
DESTRUCTIVE_PATTERNS: list[str] = [
    r"\brm\s+-rf\b",
    r"\bformat\b",
    r"\bdel\s+/s\b",
    r"\bdrop\s+database\b",
    r"\btruncate\b",
]

# Result block field length limits
MAX_SUMMARY_LENGTH: int = 500
MAX_OUTPUT_LENGTH: int = 2000

# Data query result limits
MAX_RESULT_ROWS: int = 200

# === Guardrails (Section 05) ===

# Timeout limits (token/时间/迭代上限)
MAX_TIMEOUT_SECONDS: int = 300
TEST_TIMEOUT_SECONDS: int = 120

# === Verification Loop (Layer ②) ===

# Maximum retry attempts before escalation
MAX_RETRIES: int = 3

# Delay between retries in seconds
RETRY_DELAY_SECONDS: float = 2.0

# === Hill-climbing Loop (Layer ④) ===

# Maximum trace entries to keep in memory
MAX_TRACE_ENTRIES: int = 500

# Maximum memory file size in bytes (1MB)
MAX_MEMORY_FILE_SIZE: int = 1_048_576

# === Event-driven Loop (Layer ③) ===

# Change coalescing window in milliseconds
COALESCE_WINDOW_MS: int = 500

# === File Paths ===

# Default control file path relative to project root
DEFAULT_CONTROL_FILE_PATH: str = ".kiro/loop/control.md"

# Default hook file path relative to project root
DEFAULT_HOOK_FILE_PATH: str = ".kiro/hooks/loop-controller-hook.kiro.hook"

# Memory state file path relative to project root
MEMORY_FILE_PATH: str = ".kiro/loop/memory.json"

# Trace log file path relative to project root
TRACE_FILE_PATH: str = ".kiro/loop/trace.log"

# Rollback directory relative to project root
ROLLBACK_DIR: str = ".kiro/loop/rollback"
