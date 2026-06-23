#!/usr/bin/env bash
# Universal Verification Script (Bash — macOS/Linux)
# Auto-detects project type and runs the appropriate test/build commands.
# Exit code 0 = all checks passed, non-zero = failure.

set -euo pipefail

EXIT_CODE=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Loop Engine: Universal Verification ==="
echo "Project root: $PROJECT_ROOT"

run_check() {
    local label="$1"
    shift
    echo ""
    echo "--- $label ---"
    if "$@"; then
        echo "PASSED: $label"
    else
        echo "FAILED: $label (exit code $?)"
        EXIT_CODE=1
    fi
}

# --- Node.js / JavaScript / TypeScript ---
if [ -f "package.json" ]; then
    echo ""
    echo "Detected: Node.js project"

    if grep -q '"lint"' package.json; then
        run_check "Lint" npm run lint
    fi

    if grep -q '"typecheck"' package.json; then
        run_check "Type Check" npm run typecheck
    elif [ -f "tsconfig.json" ]; then
        run_check "Type Check (tsc)" npx tsc --noEmit
    fi

    if grep -q '"test"' package.json; then
        if grep -q '"vitest"' package.json; then
            run_check "Tests" npx vitest --run
        else
            run_check "Tests" npm test
        fi
    fi

    if grep -q '"build"' package.json; then
        run_check "Build" npm run build
    fi

# --- Python ---
elif [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then
    echo ""
    echo "Detected: Python project"

    if command -v ruff &>/dev/null; then
        run_check "Lint (ruff)" ruff check .
    elif command -v flake8 &>/dev/null; then
        run_check "Lint (flake8)" flake8 .
    fi

    if command -v mypy &>/dev/null; then
        run_check "Type Check (mypy)" mypy .
    elif command -v pyright &>/dev/null; then
        run_check "Type Check (pyright)" pyright
    fi

    if command -v pytest &>/dev/null; then
        run_check "Tests (pytest)" pytest --tb=short -q
    elif [ -d "tests" ]; then
        run_check "Tests (unittest)" python -m unittest discover -s tests
    fi

# --- Go ---
elif [ -f "go.mod" ]; then
    echo ""
    echo "Detected: Go project"
    run_check "Build" go build ./...
    run_check "Vet" go vet ./...
    run_check "Tests" go test ./... -count=1

# --- Rust ---
elif [ -f "Cargo.toml" ]; then
    echo ""
    echo "Detected: Rust project"
    run_check "Check" cargo check
    run_check "Clippy" cargo clippy -- -D warnings
    run_check "Tests" cargo test

# --- Java (Maven) ---
elif [ -f "pom.xml" ]; then
    echo ""
    echo "Detected: Java (Maven) project"
    run_check "Build & Test" mvn verify -q

# --- Java (Gradle) ---
elif [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
    echo ""
    echo "Detected: Java (Gradle) project"
    run_check "Build & Test" ./gradlew build

# --- Makefile fallback ---
elif [ -f "Makefile" ]; then
    echo ""
    echo "Detected: Makefile project"
    run_check "Make test" make test

# --- No recognized project ---
else
    echo ""
    echo "WARNING: No recognized project type detected."
    echo "Looked for: package.json, pyproject.toml, setup.py, requirements.txt, go.mod, Cargo.toml, pom.xml, build.gradle, Makefile"
    EXIT_CODE=0
fi

# --- Summary ---
echo ""
echo "=== Verification Complete ==="
if [ "$EXIT_CODE" -eq 0 ]; then
    echo "STATUS: ALL CHECKS PASSED"
else
    echo "STATUS: CHECKS FAILED (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
