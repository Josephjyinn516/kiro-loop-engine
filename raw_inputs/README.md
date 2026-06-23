# Raw Inputs — Loop Engine Intake Folder

Drop your spec files, briefs, or requirement documents here to trigger the autonomous loop.

## Supported Formats
- `.html` — HTML specs or exported documents
- `.md` — Markdown briefs or requirement docs
- `.txt` — Plain text instructions

## How It Works
1. Create or paste a file into this folder
2. The `intake-trigger` hook fires automatically
3. Kiro parses the document, extracts requirements, and populates `tasks.md`
4. The autonomous loop begins executing wave by wave

## Rules
- One input file per loop session (drop a new file after the current loop completes)
- Files in this folder are never modified by the engine — they remain your source of truth
- If Kiro can't parse the file as a spec, it will ignore it silently
