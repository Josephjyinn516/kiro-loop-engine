# Kiro Loop Engine

A pip-installable plugin that implements the **full Loop Engineering architecture** for any Kiro IDE project. Write structured instruction blocks in a markdown control file, and the engine automatically observes, decides, executes, verifies, retries, and writes results back — following the complete closed-loop pattern.

## Loop Engineering Architecture

```
最小闭环 (Minimum Closed Loop):
观察状态 → 判断下一步 → 调用工具 → 接收结果 → 验证完成 → 继续/停止
Observe  → Decide     → Execute  → Receive  → Verify   → Continue/Stop
```

### Four-Layer Loop Stack (四层 Loop Stack)

| Layer | Name | Implementation |
|-------|------|---------------|
| ① | **Agent Loop** | Handler execution until task complete |
| ② | **Verification Loop** | Verify result → retry on failure → escalate |
| ③ | **Event-driven Loop** | `fileEdited` hook triggers cycles automatically |
| ④ | **Hill-climbing Loop** | Trace/eval/memory across cycles |

### Guardrails (护栏)

| Guardrail | Implementation |
|-----------|---------------|
| 可验证 (Stop conditions) | Acceptance criteria, verify commands |
| 人工审批 (Human approval) | `safety: confirmed` for destructive ops, escalation |
| Token/时间/迭代上限 | Timeout (300s/120s), max retries (default 3) |
| Trace/版本/回滚点 | Full trace log, rollback directory with file backups |
| 保持人的理解 | Results written back to control file in readable format |

## Quick Start

### Install

```bash
# Install from GitHub
pip install git+https://github.com/Josephjyinn516/kiro-loop-engine.git

# Or pin to a specific version
pip install git+https://github.com/Josephjyinn516/kiro-loop-engine.git@v2.0.0

# For local development (editable mode)
pip install -e ./kiro-loop-engine
```

Add to your project's `requirements.txt`:
```
kiro-loop-engine @ git+https://github.com/Josephjyinn516/kiro-loop-engine.git@v2.0.0
```

Or in `pyproject.toml`:
```toml
dependencies = [
    "kiro-loop-engine @ git+https://github.com/Josephjyinn516/kiro-loop-engine.git@v2.0.0",
]
```

### Initialize in a New Project

```bash
cd /path/to/your/new/project
kiro-loop init
```

This creates:
- `.kiro/loop/control.md` — control file for instruction blocks
- `.kiro/hooks/loop-controller-hook.kiro.hook` — Kiro hook for event triggering (Layer ③)
- `.kiro/loop/rollback/` — rollback directory for file backups (Guardrail)
- `.kiro/loop/memory.json` — persistent execution memory (Layer ④, created on first cycle)
- `.kiro/loop/trace.log` — human-readable execution trace (Layer ④, created on first cycle)

### Use Programmatically

```python
from kiro_loop_engine import LoopEngine

engine = LoopEngine(project_root="/path/to/project", max_retries=3)
engine.setup()            # Scaffold files (idempotent)
engine.on_file_changed()  # Trigger a full loop cycle

# Inspect execution state (Layer ④: Hill-climbing)
stats = engine.get_memory_stats()
trace = engine.get_trace(block_id="abc123")

# Rollback to previous state (Guardrail)
engine.rollback(rollback_id="block_20250623T120000Z")
```

## How It Works

```
File Edit Event → Hook (Layer ③) → LoopEngine.on_file_changed()
    → LoopController.process_cycle()
        → OBSERVE: Parser.parse(control_file) → [InstructionBlock, ...]
        → while pending blocks:
            → DECIDE: Select next pending block (document order)
            → EXECUTE: ExecutionEngine.execute(block)
                → Safety checks (Guardrails)
                → Create rollback point (Guardrail: 回滚点)
                → Handler.execute(block)
                → VERIFY (Layer ②): VerificationLoop.verify(result)
                → If failed + retryable → rollback → retry (Layer ②)
                → If retries exhausted → ESCALATE to human
                → Record trace (Layer ④)
            → RECEIVE: Get ResultBlock
            → WRITE: ResultWriter writes back to control file
            → CONTINUE/STOP: Re-parse and loop
```

## Control File Format

```markdown
## Create User Authentication Module

type: task
status: pending
priority: high
max-retries: 3
verify: python -m pytest tests/test_auth.py
accept: file exists: src/auth/jwt_handler.py

Generate a JWT authentication module at src/auth/jwt_handler.py
with login, logout, and token refresh endpoints.
```

### Metadata Fields

| Field | Values | Default | Description |
|-------|--------|---------|-------------|
| type | `task`, `change-request`, `test`, `maintenance` | (required) | Block type |
| status | `pending`, `in-progress`, `completed`, `failed`, `skipped`, `retrying`, `escalated` | `pending` | Current state |
| priority | `low`, `normal`, `high` | `normal` | Execution priority |
| safety | `confirmed` | (not set) | Required for destructive operations |
| max-retries | integer | `3` | Maximum retry attempts (Layer ②) |
| verify | shell command | (not set) | Verification command (Layer ②) |
| accept | criteria text | (not set) | Acceptance criteria (Layer ②) |

## Block Types & Handlers

| Type | Handler | What it does |
|------|---------|-------------|
| `task` | CodeGeneratorHandler | Creates new files from instructions |
| `change-request` | CodeModifierHandler | Modifies existing files atomically |
| `test` | TestRunnerHandler | Runs test files, commands, or validates behavior |
| `maintenance` | MaintenanceHandler | Refactoring, dependency updates, bug fixes |

## Verification Loop (Layer ②)

The verification loop ensures results are correct before marking complete:

```
Execute → Verify → Pass? → ✅ Complete
                → Fail? → Retry (with rollback + backoff)
                       → Exhausted? → ⚠️ Escalate to human
```

**Verification methods** (in priority order):
1. `verify: <command>` — Run a shell command, exit 0 = pass
2. `accept: <criteria>` — Pattern-based acceptance check
3. Default — Verify expected files exist after execution

**Retry behavior:**
- Exponential backoff: 2s, 4s, 8s between retries
- Files rolled back before each retry attempt
- Non-retryable errors (path violation, ambiguity) skip retry
- After max retries → status set to `escalated`

## Hill-climbing Loop (Layer ④)

Every execution action is traced to `.kiro/loop/trace.log`:

```
[2025-06-23T12:00:00Z]    EXECUTE | block=Create Auth Module              | attempt=1 | status=completed | handler=task | duration=1200ms
[2025-06-23T12:00:02Z]     VERIFY | block=Create Auth Module              | attempt=1 | status=completed | handler=task | duration=500ms
```

Memory persists in `.kiro/loop/memory.json`:
- Total cycles, blocks processed, retries, rollbacks
- Failure patterns (recurring error types)
- Recent trace history for pattern analysis

## Custom Handlers

Extend the engine with your own block types:

```python
from kiro_loop_engine import LoopEngine, BaseHandler, InstructionBlock, ResultBlock
from datetime import datetime, timezone

class DeployHandler(BaseHandler):
    def __init__(self, project_root: str):
        self.project_root = project_root

    def execute(self, block: InstructionBlock) -> ResultBlock:
        # Your deployment logic here
        return ResultBlock(
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            status="completed",
            summary="Deployed successfully.",
            output="Deployed to staging environment.",
            truncated=False,
            verified=True,
        )

engine = LoopEngine(project_root=".")
engine.register_handler("deploy", DeployHandler("."))
```

## CLI Commands

```bash
kiro-loop init              # Scaffold loop engine files in current project
kiro-loop run               # Manually trigger one processing cycle
kiro-loop status            # Show pending/completed/escalated blocks
kiro-loop trace             # Show execution trace (Layer ④)
kiro-loop trace --limit 50  # Show last 50 trace entries
kiro-loop stats             # Show memory statistics
kiro-loop rollback          # List available rollback points
kiro-loop rollback <id>     # Restore files from rollback point
```

## Architecture Mapping to Loop Engineering Framework

```
┌─────────────────────────────────────────────────────────────┐
│  Section 01: 定义 (Definition)                               │
│  Goal-driven feedback loop with acceptance signals           │
│  → InstructionBlock.accept + VerificationLoop                │
├─────────────────────────────────────────────────────────────┤
│  Section 02: 四层 Loop Stack                                 │
│                                                              │
│  ① Agent Loop                                               │
│     → ExecutionEngine + Handlers (execute until done)        │
│                                                              │
│  ② Verification Loop                                        │
│     → VerificationLoop (verify → retry → escalate)          │
│                                                              │
│  ③ Event-driven Loop                                        │
│     → fileEdited hook + change coalescing                    │
│                                                              │
│  ④ Hill-climbing Loop                                       │
│     → Tracer + ExecutionMemory (trace/eval/memory)           │
├─────────────────────────────────────────────────────────────┤
│  Section 03: 六个工程构件 (Six Constructs)                    │
│                                                              │
│  Automations  → Hook-based triggering                        │
│  Skills       → Type-specific handlers (task, test, etc.)    │
│  Connectors   → Pluggable handler system + subprocess        │
│  Memory/State → ExecutionMemory persisted to disk            │
├─────────────────────────────────────────────────────────────┤
│  Section 04: 解决的问题 (Problems Solved)                     │
│                                                              │
│  ✅ 持续推进任务    → Processes all pending blocks             │
│  ✅ 自动观察重试升级 → Verify + retry + escalate              │
│  ✅ 用验收信号定义完成 → accept/verify metadata               │
│  ✅ 接入真实工作流   → Subprocess, file I/O, hooks            │
├─────────────────────────────────────────────────────────────┤
│  Section 05: 护栏 (Guardrails)                               │
│                                                              │
│  ✅ 可验证停止条件   → Acceptance criteria + verify commands  │
│  ✅ 人工审批高风险   → safety:confirmed + escalation          │
│  ✅ 时间/迭代上限    → Timeouts (300s/120s) + max retries     │
│  ✅ Trace/版本/回滚  → trace.log + rollback directory         │
│  ✅ 保持人的理解     → Results in control file + trace CLI    │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
kiro-loop-engine/
├── pyproject.toml
├── README.md
└── kiro_loop_engine/
    ├── __init__.py           # Public API exports
    ├── engine.py             # LoopEngine facade (main entry point)
    ├── cli.py                # CLI commands (kiro-loop)
    ├── constants.py          # Configuration constants (all layers)
    ├── models.py             # InstructionBlock, ResultBlock, TraceEntry, ExecutionMemory
    ├── parser.py             # Control file markdown parser
    ├── execution_engine.py   # Agent Loop (Layer ①) with verification integration
    ├── verification.py       # Verification Loop (Layer ②): verify → retry → escalate
    ├── tracer.py             # Hill-climbing Loop (Layer ④): trace + memory + rollback
    ├── loop_controller.py    # Event-driven Loop (Layer ③): orchestrates full cycle
    ├── result_writer.py      # Writes results back to control file
    ├── safety.py             # Guardrails: path validation, timeout, destructive detection
    └── handlers/
        ├── __init__.py
        ├── base.py           # BaseHandler ABC
        ├── code_generator.py # type=task
        ├── code_modifier.py  # type=change-request
        ├── test_runner.py    # type=test
        └── maintenance.py    # type=maintenance
```

## License

MIT
