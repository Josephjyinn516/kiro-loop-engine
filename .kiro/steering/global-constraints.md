---
inclusion: always
---

# Global Constraints — Loop Engineering Engine

These rules apply to EVERY agent action during autonomous loop execution.

---

## 1. Reuse Before Creation

- Before writing ANY new function, class, or module:
  1. Search the workspace for existing implementations with similar names or signatures.
  2. Check `node_modules/`, `vendor/`, `site-packages/`, or equivalent dependency directories.
  3. If a suitable implementation exists, IMPORT it. Do NOT duplicate.
- If an existing function is 80%+ similar to what's needed, extend or wrap it rather than rewriting.

## 2. Architectural Consistency

- Match the existing project's patterns:
  - File naming convention (camelCase, snake_case, kebab-case)
  - Module organization (flat vs. nested, barrel exports, `__init__.py` patterns)
  - Error handling style (exceptions, Result types, error codes)
  - Dependency injection patterns in use
- Do NOT introduce new architectural patterns unless the task explicitly requires it and no existing pattern serves.
- When in doubt, follow the convention established by the majority of files in the same directory.

## 3. Language Standards Compliance

- Before writing code, check for:
  - `.editorconfig` — follow indent and formatting rules
  - Linter configs (`.eslintrc`, `ruff.toml`, `clippy.toml`, `.golangci.yml`) — do not introduce violations
  - `tsconfig.json` / `jsconfig.json` strict mode settings
  - Type annotation requirements (mypy, pyright strict, TypeScript strict)
- All new code MUST pass the project's existing linter without new warnings.

## 4. Minimal Change Principle

- Solve the task with the smallest diff possible.
- Do not refactor surrounding code unless the task explicitly requires it.
- Do not change import ordering, whitespace, or formatting outside the modified logic.
- One logical change per commit scope.

## 5. Dependency Discipline

- Do NOT add new external dependencies without checking:
  1. Can the standard library solve this?
  2. Is there an existing dependency that already provides this?
  3. Is the package actively maintained (>1 release in last 12 months)?
- If a dependency MUST be added, pin to an exact version.

## 6. Safety Rails

- Never execute `rm -rf`, `DROP TABLE`, or equivalent destructive commands without explicit task authorization.
- Never modify `.env`, credentials, or secret files unless the task specifically targets them.
- Never force-push, rebase shared branches, or modify git history.

## 7. Test Awareness

- If modifying a function that has existing tests, run those tests BEFORE and AFTER the change.
- If adding a new public function, add at least one happy-path test.
- Test file location must follow the project's existing convention (co-located, `__tests__/`, `tests/`, `spec/`).
