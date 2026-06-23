# MavenAgent Development Control File

<!-- 
  HOW TO USE:
  1. Write instruction blocks below (each starts with ## heading)
  2. Save this file — the Loop Engine hook triggers automatically
  3. Kiro processes each pending block in order and writes results back here
  4. Add new blocks at the bottom anytime. Don't edit completed results.

  BLOCK TYPES:
  - task:           Create new files, generate code, scaffold modules
  - change-request: Modify existing files (atomic, all-or-nothing)
  - test:           Run test commands and capture results
  - maintenance:    Refactoring, dep updates, docs cleanup
  - data-query:     Query project structure, list files, inspect code

  STATUS VALUES:
  - pending:  Ready to be processed (default)
  - skipped:  Skip this block (won't be processed)
  
  TIPS:
  - Reference files with backtick code spans: `path/to/file.py`
  - Be specific — write like you'd write a prompt in chat
  - One concern per block — don't mix unrelated changes
  - Order matters — blocks run top to bottom
  - Set status: skipped to defer a block for later
-->

<!-- ═══════════════ BACKEND ═══════════════ -->

## 1. Setup Custom Orchestration Infrastructure and Fabric Storage Layer

type: task
status: skipped
priority: high
skipped-reason: Delivered via spec workflow (pulse-agent-platform tasks 1.1–1.4, 5.1–5.2)

Configure the foundational enterprise-grade Orchestrator-Subagent skeleton using native API patterns and external configurations:

1. Initialize the primary controller pulse_orchestrator.py to manage state, handle sub-agent fallback logic, and pass execution tokens using a custom, robust orchestrator pattern without external agent frameworks.

2. Structure separate, isolated markdown system prompt files (prompts/) for the Orchestrator and each individual Sub-Agent to enforce strict output schemas and boundary guardrails.

3. Integrate competitor-handles.json as the input configuration engine defining competitor URLs, specific regional keyword clusters, and targeted locations.

4. Establish local filesystem persistence handlers to save unparsed extraction JSON files directly inside localized /data/snapshot_YYYY-MM-DD/ directories within the project repository as a secure file cache staging layer.

### Result
timestamp: 2025-01-01T00:00:00Z
status: completed (via spec)
summary: Full orchestration infrastructure delivered through spec-based task execution. Sequential brand processing with retry logic, prompt-driven sub-agents, and date-stamped JSON snapshot persistence.
output: |
  Created:
  - pulse_agent/__init__.py
  - pulse_agent/__main__.py (CLI entry: python -m pulse_agent run)
  - pulse_agent/config.py (PipelineConfig with env loading + fail-fast validation)
  - pulse_agent/orchestrator.py (sequential brand processing, failure isolation)
  - pulse_agent/retry.py (exponential backoff: 1s→2s→4s, retries on 429/5xx)
  - pulse_agent/schemas.py (Pydantic models: BrandHandle, BrandRegistry, AgentResult, etc.)
  - pulse_agent/persistence/__init__.py
  - pulse_agent/persistence/snapshot_writer.py (date-stamped /data/snapshot_YYYY-MM-DD/)
  - prompts/seo_agent.md
  - prompts/geo_agent.md
  - prompts/technical_agent.md
  - prompts/analytics_agent.md
  - competitor-handles.json (8-brand registry)
  - pyproject.toml (Python 3.11+, httpx, pydantic, bs4, boto3, tenacity)
  Tests: 21 Python test files (unit + property-based via Hypothesis)
  Build: ✓ All spec tasks 1–7 completed

## 2. Deploy Extraction Pipelines via Specialized Sub-Agents

type: task
status: skipped
priority: high
skipped-reason: Delivered via spec workflow (pulse-agent-platform tasks 2.1–2.5)

Develop modular worker scripts utilizing resilient API integrations and targeted collection mechanics:

Component A: SEO Agent (System Prompt: prompts/seo_agent.md)
1. Extract metadata components (Title, Meta Description, Canonical URLs) from competitor domains using competitor-handles.json.

2. Map on-page structural heading tags ($H_1, H_2$) to assess content formatting depth.

3. Connect to robust SERP tracking endpoints to collect non-localized national organic keyword ranking baselines.

Component B: GEO Agent (System Prompt: prompts/geo_agent.md)
1. Orchestrate regional search tracking across designated domestic territories via parameterized regional SERP API queries.

2. Isolate rank shifts and visibility variations specific to targeted regional locations as defined in the configuration matrix.

Component C: Technical Agent (System Prompt: prompts/technical_agent.md)
1. Programmatically connect to the Google PageSpeed Insights / Lighthouse API to fetch deep technical infrastructure logs.

2. Isolate core web vitals data objects (LCP, INP, CLS) alongside baseline Accessibility and SEO structural score validations.

### Result
timestamp: 2025-01-01T00:00:00Z
status: completed (via spec)
summary: All 3 extraction sub-agents implemented with full API integrations, retry logic, and partial-result handling. Each agent governed by its own markdown prompt file.
output: |
  Created:
  - pulse_agent/agents/__init__.py
  - pulse_agent/agents/base_agent.py (ABC with retry integration)
  - pulse_agent/agents/seo_agent.py (Serper API + httpx/BeautifulSoup scraper)
  - pulse_agent/agents/geo_agent.py (AWS Bedrock Claude invocation, M1-M4 metrics)
  - pulse_agent/agents/technical_agent.py (Google PageSpeed Insights API, LCP/CLS/FCP)
  Capabilities:
  - SEO: SERP keyword positions, title/meta/canonical/headings extraction, schema detection
  - GEO: AI engine simulation via Bedrock, brand mention counting, sentiment scoring
  - Technical: Lighthouse mobile+desktop, CWV metrics, accessibility score
  - All agents: exponential backoff retry, partial result on scrape failure
  Tests: test_seo_agent.py, test_base_agent.py, test_technical_agent.py + property test for schema conformance
  Build: ✓ All spec tasks 2.1–2.5 completed

## 3. Implement Manual-Driven Scoring Engine (Analytics Agent)
type: task
status: skipped
priority: high
skipped-reason: Delivered via spec workflow (pulse-agent-platform tasks 3.1–3.7). Note — Fabric push not implemented; local JSON persistence used instead per spec design.

Develop the quantitative evaluation layer (analytics_scoring_engine.py, System Prompt: prompts/analytics_agent.md):
1. Ingest raw extraction objects compiled by the SEO, GEO, and Technical sub-agents.

2. Ingest explicit user scoring methodology definitions from website-seo-scoring-methodology.md and geo-scoring-methodology.md.

3. Compute finalized standardized scores ($0-100$) and map them directly into a normalized relational data model featuring dedicated keys for combined_score, component breakdown JSON blobs, keyword triggers, and historical delta records.

4. Open network links to authenticate and push the finalized clean analytical outputs directly into production Microsoft Fabric tables (DW_Competitor_Intelligence.dw_weekly_snapshot).

### Result
timestamp: 2025-01-01T00:00:00Z
status: completed (via spec — local persistence; Fabric push deferred)
summary: Deterministic scoring engines implemented for both SEO (4-dimension, 100-point) and GEO (4-metric weighted hybrid). Results persisted as local JSON snapshots. Microsoft Fabric integration not in spec scope.
output: |
  Created:
  - pulse_agent/scoring/__init__.py
  - pulse_agent/scoring/seo_scoring.py (Tech Foundation 25 + Schema 25 + Performance 30 + Content 20 = 100)
  - pulse_agent/scoring/geo_scoring.py (M1×0.30 + M2×0.25 + M3×0.20 + M4×0.25)
  Scoring Details:
  - SEO grades: A(80-100), B(60-79), C(40-59), D(20-39), F(0-19)
  - GEO bands: Dominant(81-100), Strong(61-80), Developing(41-60), Weak(21-40), Critical(0-20)
  - M2 SOV bracket system: 0%→0, 5-19%→25, 20-50%→50, >50%→75, sole→100
  - M4 recency defaults to 0 when no FM sources cited
  Tests: 5 property-based tests (scoring bounds, classification mapping, composite formula, SOV brackets, recency default)
  Not implemented: Microsoft Fabric push (deferred — use snapshot JSON for now)
  Build: ✓ All spec tasks 3.1–3.7 completed

<!-- ═══════════════ FRONTEND ═══════════════ -->

## 4. Map Structured Data Layers to Dashboard Steering Specifications
type: task
status: skipped
priority: high
skipped-reason: Delivered via spec workflow (pulse-agent-platform tasks 8.1–10.6)

Configure the output contract to map smoothly to your 4-tab dashboard UI framework (Overview, SEO, GEO, Technical Files):

1. Format data pipelines to support macro data metrics for the Overview tab, specifically optimizing schema structures for combined score bar charts, clustered score component columns, and historical tracking line components.

2. Unpack categorical metric breakdowns and nested keyword_triggers JSON objects to supply individual tab views with performant data payloads out-of-the-box.

3. Incorporate explicit logic flags derived from the scoring methodology files to expose core functional gaps (like severe Core Web Vital failures or regional ranking drops) inside the front-end layout grid components.

### Result
timestamp: 2025-01-01T00:00:00Z
status: completed (via spec)
summary: Full Next.js 14 dashboard with 4-tab layout reading from snapshot JSON. Includes bar charts, trend lines, dimension breakdowns, keyword tables, CWV indicators, and gap warnings.
output: |
  Created:
  - dashboard/package.json (Next.js 14, React 18, Recharts, Tailwind, shadcn/ui)
  - dashboard/app/layout.tsx (root layout + TabNavigation)
  - dashboard/app/page.tsx (Overview: SEO+GEO bar charts, trend line, FamilyMart highlight)
  - dashboard/app/seo/page.tsx (4-dimension breakdown, keyword table, gap warnings)
  - dashboard/app/geo/page.tsx (M1-M4 metrics, band display, sentiment descriptors)
  - dashboard/app/technical/page.tsx (CWV color-coded, Lighthouse mobile+desktop, accessibility)
  - dashboard/components/charts/ScoreBarChart.tsx
  - dashboard/components/charts/TrendLineChart.tsx
  - dashboard/components/charts/DimensionBreakdown.tsx
  - dashboard/components/tables/KeywordRankingTable.tsx
  - dashboard/components/tables/MetricTable.tsx
  - dashboard/components/indicators/GapWarning.tsx
  - dashboard/components/indicators/CwvIndicator.tsx
  - dashboard/components/TabNavigation.tsx
  - dashboard/lib/types.ts (TypeScript interfaces matching JSON schemas)
  - dashboard/lib/snapshot-loader.ts (reads latest snapshot from /data/)
  - dashboard/lib/thresholds.ts (CWV thresholds, statusToColor, hasCriticalGap)
  Tests: 3 property-based tests (CWV thresholds, critical gap detection, snapshot loading)
  Build: ✓ All spec tasks 8.1–10.6 completed

<!-- ═══════════════ TESTS ═══════════════ -->

##

<!-- ═══════════════ MAINTENANCE ═══════════════ -->

##
