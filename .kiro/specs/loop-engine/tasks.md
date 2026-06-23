# Loop Engineering Engine — Task Dependency Graph

## Template Structure

This file serves as both the master template and the live execution tracker.
When a new goal is initiated, Kiro clones this wave structure and populates it with concrete tasks derived from the user's intent.

---

## Wave 1: Discovery & Analysis

**Purpose:** Understand the codebase, map dependencies, identify constraints before writing any code.

- [ ] `1.1` — Scan workspace for project manifest files and determine language/framework/build tool
  - Success: A structured summary of detected toolchain is written to context
  - Depends on: (none — entry point)

- [ ] `1.2` — Identify existing architectural patterns (module structure, naming conventions, test layout)
  - Success: Pattern summary matches actual directory structure (spot-checked against 3 paths)
  - Depends on: 1.1

- [ ] `1.3` — Map file-level dependencies relevant to the user's goal
  - Success: Dependency list produced; no missing imports when cross-referenced with task scope
  - Depends on: 1.1

- [ ] `1.4` — Identify existing tests and coverage gaps related to the goal
  - Success: List of relevant test files and untested paths produced
  - Depends on: 1.2, 1.3

- [ ] `1.5` — Produce execution plan: ordered list of implementation tasks for Wave 2
  - Success: Plan references specific files, functions, and line ranges; no ambiguous steps
  - Depends on: 1.1–1.4

---

## Wave 2: Implementation

**Purpose:** Execute the plan produced in Wave 1. Each task creates or modifies exactly one logical unit.

- [ ] `2.1` — (Template) Create/modify primary module or entry point
  - Success: File exists, passes lint, imports resolve
  - Depends on: 1.5

- [ ] `2.2` — (Template) Implement core logic / business rules
  - Success: Unit tests pass for the new logic; no regressions in existing tests
  - Depends on: 2.1

- [ ] `2.3` — (Template) Wire integrations (API calls, DB access, IPC)
  - Success: Integration point responds correctly in isolation (mock or real)
  - Depends on: 2.2

- [ ] `2.4` — (Template) Update configuration / environment files
  - Success: Application boots successfully with new config
  - Depends on: 2.1–2.3

- [ ] `2.5` — (Template) Add/update documentation (inline + README)
  - Success: No undocumented public exports; README reflects new capability
  - Depends on: 2.1–2.4

---

## Wave 3: Verification & Hardening

**Purpose:** Prove correctness, handle edge cases, ensure production readiness.

- [ ] `3.1` — Run full test suite via `.kiro/scripts/verify.sh`
  - Success: Exit code 0; no new warnings introduced
  - Depends on: Wave 2 complete

- [ ] `3.2` — Verify no regressions (compare test output before vs. after)
  - Success: Test count ≥ prior count; no previously-passing test now fails
  - Depends on: 3.1

- [ ] `3.3` — Static analysis / lint pass
  - Success: Zero new lint errors (existing baseline exempted)
  - Depends on: 3.1

- [ ] `3.4` — Edge case hardening (null inputs, boundary values, error paths)
  - Success: Added ≥1 edge-case test per public function introduced in Wave 2
  - Depends on: 3.2

- [ ] `3.5` — Final integration smoke test
  - Success: End-to-end scenario completes without error
  - Depends on: 3.1–3.4

- [ ] `3.6` — Update tasks.md — mark all tasks done, write completion summary
  - Success: All checkboxes checked; summary block appended
  - Depends on: 3.5

---

## State Legend

| Symbol | Meaning |
|--------|---------|
| `[ ]` | Pending |
| `[~]` | In Progress |
| `[x]` | Done |
| `[!]` | Failed (awaiting retry or user input) |
| `[-]` | Blocked |

---

## Execution Rules

1. Process waves sequentially (1 → 2 → 3).
2. Within a wave, tasks with satisfied dependencies MAY run in parallel.
3. On task failure: enter self-correction loop (max 3 retries).
4. After 3 failures: mark task `[!]`, halt wave, notify user.
5. On wave completion: log timestamp and advance to next wave.

---

## Completion Summary

<!-- Auto-populated by the engine on successful completion of Wave 3 -->

```
Goal:
Started:
Completed:
Total Tasks:
Retries Used:
Final Status:
```
