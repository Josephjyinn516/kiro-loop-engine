# Kiro Loop Engine

A reusable, pip-installable plugin that provides file-driven automation for any Kiro IDE project. Write structured instruction blocks in a markdown control file, and the engine parses, executes, and writes results back automatically.

## Quick Start

### Install

```bash
# From the package directory (editable/development mode)
pip install -e ./kiro-loop-engine

# Or build and install from wheel
cd kiro-loop-engine
pip install .
```

### Initialize in a New Project

```bash
cd /path/to/your/new/project
kiro-loop init
```

This creates:
- `.kiro/loop/control.md` — the control file where you write instruction blocks
- `.kiro/hooks/loop-controller-hook.kiro.hook` — Kiro hook that auto-triggers the engine on save

### Use Programmatically

```python
from kiro_loop_engine import LoopEngine

engine = LoopEngine(project_root="/path/to/project")
engine.setup()            # Scaffold files (idempotent)
engine.on_file_changed()  # Trigger a parse-execute-write cycle
```

## How It Works

1. **You write** instruction blocks in `.kiro/loop/control.md` as H2 markdown sections
2. **Kiro hook detects** the file save and triggers the engine
3. **Engine parses** the control file into structured `InstructionBlock` objects
4. **Safety checks** validate paths stay within project boundaries and block destructive commands
5. **Type-specific handlers** execute each pending block (task, change-request, test, maintenance)
6. **Results are written** back into the control file as `### Result` sub-sections

## Control File Format

```markdown
## Create User Authentication Module

type: task
status: pending
priority: high

Generate a JWT authentication module at src/auth/jwt_handler.py
with login, logout, and token refresh endpoints.
```

### Metadata Fields

| Field | Values | Default |
|-------|--------|---------|
| type | `task`, `change-request`, `test`, `maintenance` | (required) |
| status | `pending`, `in-progress`, `completed`, `failed`, `skipped` | `pending` |
| priority | `low`, `normal`, `high` | `normal` |
| safety | `confirmed` | (not set) |

## Block Types & Handlers

| Type | Handler | What it does |
|------|---------|-------------|
| `task` | CodeGeneratorHandler | Creates new files from instructions |
| `change-request` | CodeModifierHandler | Modifies existing files atomically |
| `test` | TestRunnerHandler | Runs test files, commands, or validates behavior |
| `maintenance` | MaintenanceHandler | Refactoring, dependency updates, bug fixes |

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
        )

engine = LoopEngine(project_root=".")
engine.register_handler("deploy", DeployHandler("."))
```

Then use it in your control file:

```markdown
## Deploy to Staging

type: deploy
status: pending
priority: high

Deploy the latest build to staging environment.
```

## CLI Commands

```bash
kiro-loop init      # Scaffold loop engine files in current project
kiro-loop run       # Manually trigger one processing cycle
kiro-loop status    # Show pending/completed blocks in control file
```

## Safety Guardrails

- **Path boundary enforcement**: All file operations are restricted to the project root
- **Destructive command detection**: Commands matching `rm -rf`, `drop database`, etc. require explicit `safety: confirmed`
- **Timeout enforcement**: 300s for general blocks, 120s for test blocks
- **Atomicity**: Change-request blocks validate all target files exist before modifying any

## Project Structure

```
kiro-loop-engine/
├── pyproject.toml
├── README.md
└── src/
    └── kiro_loop_engine/
        ├── __init__.py          # Public API exports
        ├── engine.py            # LoopEngine facade (main entry point)
        ├── cli.py               # CLI commands (kiro-loop)
        ├── constants.py         # Configuration constants
        ├── models.py            # InstructionBlock, ResultBlock dataclasses
        ├── parser.py            # Control file markdown parser
        ├── execution_engine.py  # Routes blocks to handlers with safety
        ├── loop_controller.py   # Orchestrates parse-execute-write cycle
        ├── result_writer.py     # Writes results back to control file
        ├── safety.py            # Path validation, timeout, destructive detection
        └── handlers/
            ├── __init__.py
            ├── base.py              # BaseHandler ABC
            ├── code_generator.py    # type=task
            ├── code_modifier.py     # type=change-request
            ├── test_runner.py       # type=test
            └── maintenance.py       # type=maintenance
```

## License

MIT
