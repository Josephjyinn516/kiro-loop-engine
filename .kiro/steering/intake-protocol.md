---
inclusion: fileMatch
fileMatchPattern: "*.html,*.md,*.txt,*.pdf"
---

# Intake Protocol — Material-Driven Loop Trigger

When a file matching this pattern is read into context, treat it as a potential **loop input document** — a source of requirements that should be decomposed into the wave-based task graph.

---

## Recognition

A file is a valid loop input if it contains ANY of:
- A heading or section labeled "requirements", "spec", "brief", "goal", or "instructions"
- A list of deliverables, constraints, or acceptance criteria
- A description of something to build, fix, or change

If the file is just regular source code or configuration, ignore this protocol.

---

## Decomposition Process

When a valid loop input is detected:

1. **Extract the goal** — Summarize the user's intent in one sentence.
2. **Identify constraints** — List all explicit rules, limitations, and technical requirements.
3. **Break into atomic tasks** — Each task must:
   - Map to exactly one file creation or modification
   - Have testable success criteria derived from the constraints
   - Fit the Wave structure (Discovery → Implementation → Verification)
4. **Populate tasks.md** — Write the concrete tasks into `.kiro/specs/loop-engine/tasks.md`, replacing the template placeholders with real task descriptions.
5. **Begin execution** — Start Wave 1, Task 1.1.

---

## File Location Conventions

Accepted input locations:
- Project root (any `.html`, `.md`, `.txt` file with spec-like content)
- `.raw_inputs/` directory (dedicated intake folder)
- Dragged into chat as an attachment

---

## Example Transformation

**Input (HTML):**
```html
<h1>Transaction Receipt Layout</h1>
<p>Build a responsive HTML email template for order confirmations.</p>
<ul>
  <li>Must use nested HTML tables for layout</li>
  <li>No flexbox or CSS grid</li>
  <li>Include placeholder: {{ORDER_ID}}</li>
</ul>
```

**Output (tasks.md Wave 2 excerpt):**
```
- [ ] 2.1 — Create HTML email template with nested table layout
  - Success: Valid HTML; uses only <table> for structure; no display:flex or display:grid
  - Depends on: 1.5

- [ ] 2.2 — Add dynamic placeholder {{ORDER_ID}} in order summary section
  - Success: Placeholder appears in rendered output; grep finds exactly "{{ORDER_ID}}"
  - Depends on: 2.1

- [ ] 2.3 — Ensure responsive behavior via table width attributes and media queries
  - Success: Renders correctly at 320px and 600px viewport widths
  - Depends on: 2.1
```

---

## Rules

- NEVER start implementation before completing Wave 1 (Discovery).
- ALWAYS preserve the original input file untouched — it's the source of truth.
- If the input is ambiguous, list assumptions explicitly before proceeding.
- If the input conflicts with global-constraints.md, the constraints win.
