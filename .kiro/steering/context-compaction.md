---
inclusion: always
---

# Context Compaction Protocol

When operating in long autonomous loops, context windows fill up. This steering file defines how Kiro should summarize its own history to preserve critical information while discarding noise.

---

## When to Compact

Compact proactively when:
- You estimate you've used >60% of available context
- A wave boundary is reached (transitioning from Wave N to Wave N+1)
- More than 10 tool calls have occurred since the last compaction

---

## What to ALWAYS Preserve

These items MUST survive every compaction round:

1. **Original User Goal** — The exact text of the user's initial intent (verbatim, quoted)
2. **Current Wave & Task** — Which wave you're in, which task is active
3. **Active Task Success Criteria** — The exact criteria for the current task
4. **Latest Failure Context** — The most recent error message, stack trace, and the diff that caused it (last 2 failures max)
5. **File Dependency Map** — List of files currently being modified and their roles
6. **Retry Counter** — How many retries have been used on the current task (out of 3)
7. **Decisions Made** — Key architectural or implementation decisions and WHY they were made

---

## What to DISCARD

These may be safely discarded during compaction:

- Historical tool call outputs from completed tasks (keep only the summary)
- Intermediate file reads that have been superseded by edits
- Exploration paths that were abandoned (dead ends)
- Verbose build output from PASSING runs (keep only "passed" status)
- Redundant re-reads of files already in working memory

---

## Compaction Format

When compacting, produce a structured summary block:

```
## Loop State Snapshot

**Goal:** "<original user goal verbatim>"
**Progress:** Wave X, Task X.Y (status)
**Retries Used:** N/3 on current task

### Completed Tasks
- 1.1: <one-line summary> ✓
- 1.2: <one-line summary> ✓
...

### Active Context
- Working files: [list]
- Key decisions: [list]
- Current approach: <1-2 sentences>

### Latest Errors (if any)
```
<most recent error output, max 50 lines>
```

### Next Steps
1. <immediate next action>
2. <following action>
```

---

## Rules

- NEVER discard the original goal — it anchors the entire loop.
- NEVER discard active failure logs — they're needed for self-correction.
- ALWAYS keep the tasks.md checkbox state as the canonical progress record.
- When uncertain whether to keep or discard, keep it through one more cycle then discard.
- Compaction is INTERNAL — do not surface the compaction process to the user unless they ask.
