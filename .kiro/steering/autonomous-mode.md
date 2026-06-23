---
inclusion: always
---

# Autonomous Execution Mode

This workspace operates in FULLY AUTONOMOUS mode. The loop engine runs end-to-end without human intervention.

---

## Core Directive

**NEVER ask the user for permission to proceed between steps.**

This means:
- Do NOT ask "Would you like me to proceed?"
- Do NOT ask "Would you like to start executing?"
- Do NOT ask "Would you like to review X first?"
- Do NOT present menus of options (e.g., "Generate Tech Design / Generate Task List / Analyze Requirements")
- Do NOT wait for confirmation between requirements → design → tasks → implementation
- Do NOT pause after completing one spec document to ask about the next

---

## Expected Flow

When any spec or task pipeline is initiated, execute ALL steps through the loop engine:

```
raw_input → parse to control.md blocks → engine.process_cycle() → verify → trace → done
```

The loop engine (`kiro_loop_engine`) is the orchestrator. Do NOT bypass it:
- Intake: Parse raw inputs into instruction blocks in `.kiro/loop/control.md`
- Execution: The engine routes blocks to handlers, verifies results, retries on failure
- Tracing: All actions are recorded via the engine's tracer (Layer ④)
- Rollback: The engine creates rollback points before modifying files
- State: `.kiro/loop/control.md` is the canonical execution state (not just tasks.md)

Each transition happens IMMEDIATELY. No pauses. No confirmations. No choices.

---

## When to ACTUALLY Stop

Only stop execution if:
1. A task has failed 3 times (self-correction exhausted)
2. A destructive action is required (per global-constraints.md safety rails)
3. The input document is ambiguous and genuinely cannot be interpreted
4. All waves are complete (success)

---

## Applying to Spec Workflows

When Kiro's built-in spec workflow offers choices like "Generate Tech Design" or "Generate Task List":
- Select ALL of them automatically in sequence
- Do not present them to the user
- Treat the spec workflow as a pipeline, not a menu
