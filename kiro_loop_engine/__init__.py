"""Kiro Loop Engine - Full Loop Engineering architecture for Kiro IDE.

Implements the complete Loop Engineering framework:
    Layer ①: Agent Loop (observe → decide → execute → receive → verify → continue/stop)
    Layer ②: Verification Loop (auto-verify, retry on failure, escalate to human)
    Layer ③: Event-driven Loop (fileEdited hook, change coalescing)
    Layer ④: Hill-climbing Loop (trace, eval, memory across cycles)

    Guardrails:
    - Path boundary enforcement
    - Destructive command detection + human approval
    - Timeout/iteration limits
    - Trace, versioning, rollback points
    - Human-readable results

Usage:
    from kiro_loop_engine import LoopEngine

    # Initialize in your project
    engine = LoopEngine(project_root="/path/to/project")
    engine.setup()            # Creates control file, hooks, memory, rollback dir
    engine.on_file_changed()  # Trigger a full loop cycle

    # Inspect execution state (Layer ④)
    stats = engine.get_memory_stats()
    trace = engine.get_trace(block_id="abc123")

    # Rollback (Guardrail)
    engine.rollback(rollback_id="block_20250623T120000Z")

    # Or use the CLI
    # $ kiro-loop init      # Scaffold loop files in current project
    # $ kiro-loop run       # Manually trigger one cycle
    # $ kiro-loop status    # Show pending/completed blocks
    # $ kiro-loop trace     # Show execution trace
"""

from kiro_loop_engine.constants import (
    COALESCE_WINDOW_MS,
    DESTRUCTIVE_PATTERNS,
    MAX_OUTPUT_LENGTH,
    MAX_RESULT_ROWS,
    MAX_RETRIES,
    MAX_SUMMARY_LENGTH,
    MAX_TIMEOUT_SECONDS,
    MAX_TRACE_ENTRIES,
    MEMORY_FILE_PATH,
    ROLLBACK_DIR,
    TEST_TIMEOUT_SECONDS,
    TRACE_FILE_PATH,
    VALID_PRIORITIES,
    VALID_STATUSES,
    VALID_TYPES,
)
from kiro_loop_engine.engine import LoopEngine
from kiro_loop_engine.execution_engine import ExecutionEngine
from kiro_loop_engine.handlers.base import BaseHandler
from kiro_loop_engine.handlers.code_generator import CodeGeneratorHandler
from kiro_loop_engine.handlers.code_modifier import CodeModifierHandler
from kiro_loop_engine.handlers.maintenance import MaintenanceHandler
from kiro_loop_engine.handlers.test_runner import TestRunnerHandler
from kiro_loop_engine.loop_controller import LoopController
from kiro_loop_engine.models import ExecutionMemory, InstructionBlock, ResultBlock, TraceEntry
from kiro_loop_engine.parser import Parser
from kiro_loop_engine.result_writer import ResultWriter
from kiro_loop_engine.tracer import Tracer
from kiro_loop_engine.verification import VerificationLoop

__version__ = "2.0.0"

__all__ = [
    # Core
    "LoopEngine",
    "LoopController",
    "ExecutionEngine",
    "Parser",
    "ResultWriter",
    # Loop layers
    "VerificationLoop",
    "Tracer",
    # Handlers
    "BaseHandler",
    "CodeGeneratorHandler",
    "CodeModifierHandler",
    "MaintenanceHandler",
    "TestRunnerHandler",
    # Models
    "InstructionBlock",
    "ResultBlock",
    "TraceEntry",
    "ExecutionMemory",
    # Constants
    "VALID_TYPES",
    "VALID_STATUSES",
    "VALID_PRIORITIES",
    "MAX_RETRIES",
]
