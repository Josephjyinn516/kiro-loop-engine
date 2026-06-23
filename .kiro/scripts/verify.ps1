# Universal Verification Script (PowerShell - Windows)
# Auto-detects project type and runs the appropriate test/build commands.
# Exit code 0 = all checks passed, non-zero = failure.

$ErrorActionPreference = "Continue"
$script:exitCode = 0

Write-Host "=== Loop Engine: Universal Verification ===" -ForegroundColor Cyan

# --- Detect project root (walk up from script location) ---
$projectRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
Set-Location $projectRoot
Write-Host "Project root: $projectRoot"

# --- Detection and Execution ---

function Run-Check {
    param([string]$Label, [string]$Command)
    Write-Host ""
    Write-Host "--- $Label ---" -ForegroundColor Yellow
    Invoke-Expression $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $Label (exit code $LASTEXITCODE)" -ForegroundColor Red
        $script:exitCode = $LASTEXITCODE
    }
    else {
        Write-Host "PASSED: $Label" -ForegroundColor Green
    }
}

# --- Node.js / JavaScript / TypeScript ---
if (Test-Path "package.json") {
    Write-Host ""
    Write-Host "Detected: Node.js project" -ForegroundColor Magenta
    $pkg = Get-Content "package.json" | ConvertFrom-Json

    if ($pkg.scripts.lint) {
        Run-Check "Lint" "npm run lint"
    }
    if ($pkg.scripts.typecheck) {
        Run-Check "Type Check" "npm run typecheck"
    }
    elseif (Test-Path "tsconfig.json") {
        Run-Check "Type Check (tsc)" "npx tsc --noEmit"
    }
    if ($pkg.scripts.test) {
        $testCmd = "npm test"
        if ($pkg.devDependencies.vitest -or $pkg.dependencies.vitest) {
            $testCmd = "npx vitest --run"
        }
        Run-Check "Tests" $testCmd
    }
    if ($pkg.scripts.build) {
        Run-Check "Build" "npm run build"
    }
}

# --- Python ---
elseif ((Test-Path "pyproject.toml") -or (Test-Path "setup.py") -or (Test-Path "requirements.txt")) {
    Write-Host ""
    Write-Host "Detected: Python project" -ForegroundColor Magenta

    if (Get-Command "ruff" -ErrorAction SilentlyContinue) {
        Run-Check "Lint (ruff)" "ruff check ."
    }
    elseif (Get-Command "flake8" -ErrorAction SilentlyContinue) {
        Run-Check "Lint (flake8)" "flake8 ."
    }

    if (Get-Command "mypy" -ErrorAction SilentlyContinue) {
        Run-Check "Type Check (mypy)" "mypy ."
    }
    elseif (Get-Command "pyright" -ErrorAction SilentlyContinue) {
        Run-Check "Type Check (pyright)" "pyright"
    }

    if (Get-Command "pytest" -ErrorAction SilentlyContinue) {
        Run-Check "Tests (pytest)" "pytest --tb=short -q"
    }
    elseif (Test-Path "tests") {
        Run-Check "Tests (unittest)" "python -m unittest discover -s tests"
    }
}

# --- Go ---
elseif (Test-Path "go.mod") {
    Write-Host ""
    Write-Host "Detected: Go project" -ForegroundColor Magenta
    Run-Check "Build" "go build ./..."
    Run-Check "Vet" "go vet ./..."
    Run-Check "Tests" "go test ./... -count=1"
}

# --- Rust ---
elseif (Test-Path "Cargo.toml") {
    Write-Host ""
    Write-Host "Detected: Rust project" -ForegroundColor Magenta
    Run-Check "Check" "cargo check"
    Run-Check "Clippy" "cargo clippy -- -D warnings"
    Run-Check "Tests" "cargo test"
}

# --- Java (Maven) ---
elseif (Test-Path "pom.xml") {
    Write-Host ""
    Write-Host "Detected: Java (Maven) project" -ForegroundColor Magenta
    Run-Check "Maven Build" "mvn verify -q"
}

# --- Java (Gradle) ---
elseif ((Test-Path "build.gradle") -or (Test-Path "build.gradle.kts")) {
    Write-Host ""
    Write-Host "Detected: Java (Gradle) project" -ForegroundColor Magenta
    Run-Check "Gradle Build" "gradle build"
}

# --- Makefile fallback ---
elseif (Test-Path "Makefile") {
    Write-Host ""
    Write-Host "Detected: Makefile project" -ForegroundColor Magenta
    Run-Check "Make test" "make test"
}

# --- No recognized project ---
else {
    Write-Host ""
    Write-Host "WARNING: No recognized project type detected." -ForegroundColor Yellow
    Write-Host "Looked for: package.json, pyproject.toml, setup.py, requirements.txt, go.mod, Cargo.toml, pom.xml, build.gradle, Makefile"
    $script:exitCode = 0
}

# --- Summary ---
Write-Host ""
Write-Host "=== Verification Complete ===" -ForegroundColor Cyan
if ($script:exitCode -eq 0) {
    Write-Host "STATUS: ALL CHECKS PASSED" -ForegroundColor Green
}
else {
    Write-Host "STATUS: CHECKS FAILED (exit code: $($script:exitCode))" -ForegroundColor Red
}

exit $script:exitCode
