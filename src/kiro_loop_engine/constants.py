"""Constants for the Kiro Loop Engine."""

# Valid instruction block types
VALID_TYPES: list[str] = ["task", "change-request", "test", "maintenance"]

# Valid instruction block statuses
VALID_STATUSES: list[str] = ["pending", "in-progress", "completed", "failed", "skipped"]

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

# Timeout limits
MAX_TIMEOUT_SECONDS: int = 300
TEST_TIMEOUT_SECONDS: int = 120

# Change coalescing window in milliseconds
COALESCE_WINDOW_MS: int = 500

# Default control file path relative to project root
DEFAULT_CONTROL_FILE_PATH: str = ".kiro/loop/control.md"

# Default hook file path relative to project root
DEFAULT_HOOK_FILE_PATH: str = ".kiro/hooks/loop-controller-hook.kiro.hook"
