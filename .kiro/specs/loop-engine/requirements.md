# Loop Engineering Engine — Requirements

## Purpose

Define how Kiro autonomously decomposes any broad user intent into discrete, verifiable engineering tasks and executes them through a self-correcting loop until completion.

---

## Functional Requirements

### FR-1: Intent Decomposition

- Given any natural-language user goal, Kiro MUST break it into atomic engineering tasks.
- Each task MUST have:
  - A unique identifier (wave.sequence, e.g., `1.3`)
  - A plain-language description of the deliverable
  - Explicit input dependencies (files, data, prior tasks)
  - Explicit success criteria (testable assertions, not subjective measures)
  - An estimated complexity tag: `trivial | small | medium | large`

### FR-2: Dependency Resolution

- Tasks MUST be organized into dependency waves (see tasks.md).
- Tasks within a wave MAY execute in parallel if they share no file-level dependencies.
- A wave MUST NOT begin until all tasks in the prior wave have status `done`.

### FR-3: Verification Gate

- Every task MUST pass its success criteria before being marked `done`.
- Verification is performed by the universal verify script (`.kiro/scripts/verify.sh`) or task-specific assertions.
- A task that fails verification enters the self-correction loop (max 3 retries).

### FR-4: Self-Correction Loop

- On failure, Kiro MUST:
  1. Capture the full error output.
  2. Diff the last change against the prior working state.
  3. Consult relevant steering files for constraints.
  4. Produce a targeted fix (not a rewrite).
  5. Re-run verification.
- After 3 consecutive failures on the same task, Kiro MUST stop and report to the user with a root-cause hypothesis.

### FR-5: State Persistence

- Task state MUST be persisted in `tasks.md` using checkbox syntax.
- State transitions: `pending` → `in_progress` → `done` | `failed` | `blocked`
- Kiro MUST NOT lose progress on context compaction; the tasks.md file is the source of truth.

### FR-6: Language Agnosticism

- The engine MUST NOT assume any specific programming language, framework, or build tool.
- Detection of project type is handled dynamically by inspecting manifest files (package.json, go.mod, Cargo.toml, pyproject.toml, pom.xml, Makefile, etc.).

---

## Non-Functional Requirements

### NFR-1: Token Efficiency

- Steering files use `fileMatch` patterns to load only when relevant files are in context.
- Context compaction steering ensures long loops discard historical noise.

### NFR-2: Determinism

- Given the same project state and task definition, the engine MUST produce the same execution plan.

### NFR-3: Observability

- Every state transition MUST be logged in tasks.md with a timestamp comment.
- The control file (`.kiro/loop/control.md`) remains the human-readable audit trail.

### NFR-4: Safety

- Destructive operations (file deletion, dependency removal) require an explicit confirmation step unless the task's success criteria explicitly call for removal.
- The engine MUST NOT push to remote repositories without explicit user instruction.

---

## Actors

| Actor | Role |
|-------|------|
| User | Provides initial intent; reviews failed tasks; approves destructive actions |
| Kiro (Agent) | Decomposes, executes, verifies, self-corrects |
| Verify Script | Language-agnostic build/test oracle |
| Hooks | Event-driven glue wiring the autonomous loop |

---

## Acceptance Criteria (Engine-Level)

1. A user writes a single sentence goal → Kiro produces a complete tasks.md with ≥3 waves.
2. Kiro executes all waves without human intervention on a green-path scenario.
3. On a deliberate test failure injection, the self-correction loop fixes it within 3 retries.
4. The engine works on a Node.js repo, a Python repo, and a Rust repo without modification.
