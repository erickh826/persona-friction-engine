# 🤖 AGENTS.md — Multi-Agent Collaboration Guide

This file is the **single source of truth** for all AI agents (Manus, Cursor, Copilot, and others) working on this repository. Read this file before starting any work.

---

## 📌 Collaboration Rules (協作規則)

1. **Schema-First**: All module boundaries are defined by `schemas/`. Never change a schema without creating a PR discussion first.
2. **Branch-Per-Module**: Each agent works on its own `feature/<module-name>` branch. Never commit directly to `main`.
3. **Mock-First**: Every module must have a working mock before integrating with other modules.
4. **PR Required**: All changes must go through a Pull Request. PRs must pass CI tests before merging.
5. **AGENTS.md is canonical**: If AGENTS.md conflicts with any other doc, AGENTS.md wins.

---

## ✅ M1 — COMPLETED (已完成)

All M1 modules have been merged to `main`. 27 tests passing.

| Module | Agent | Status |
| :--- | :--- | :--- |
| Persona Engine | Copilot | ✅ Merged |
| Navigation Engine | Cursor | ✅ Merged |
| Evaluation Engine (Rule-based CLS) | Cursor | ✅ Merged |
| Orchestrator + CLI | Manus | ✅ Merged |

---

## ✅ M2 — COMPLETED (已完成)

All M2 modules have been merged to `main`. 42 tests passing.

| Module | Agent | Status |
| :--- | :--- | :--- |
| LLM Persona Engine (dynamic cognitive state) | Copilot | ✅ Merged |
| Vision Evaluation (GPT-4o screenshot analysis) | Cursor | ✅ Merged |
| Interactive HTML Report (Tailwind + Chart.js) | Cursor | ✅ Merged |
| Orchestrator Integration (real engines + error recovery) | Manus | ✅ Merged |

---

## 🚧 M3 — IN PROGRESS (進行中)

**Goal**: Transform the engine into a CI/CD-integrated, self-serve SaaS platform with academic-grade Friction Score credibility.

**M3 目標**：將引擎轉化為 CI/CD 整合、自助式 SaaS 平台，並建立具學術公信力的 Friction Score 標準。

### Branch Assignment (分支任務分配)

| Branch | Agent | Module |
| :--- | :--- | :--- |
| `feature/m3-github-action` | **Manus** | CI/CD GitHub Action Plugin |
| `feature/m3-dynamic-persona` | **Copilot** | GA-Integrated Dynamic Persona Engine |
| `feature/m3-saas-api` | **Cursor** | Self-Serve REST API + Auth Layer |
| `feature/m3-benchmark-report` | **Cursor** | 50 Top E-Commerce Benchmark Report Generator |

---

### 📋 `feature/m3-github-action` — Manus

**Goal**: Build a GitHub Action that runs a friction audit on every PR, blocking merges if CLS exceeds a configurable threshold.

**目標**：建立一個 GitHub Action，在每個 PR 上執行摩擦力審計，當 CLS 超過可配置閾值時阻止合併。

- [ ] **Task 1.1**: Create `action.yml` with inputs: `scenario_path`, `target_url`, `cls_threshold`, `fail_on_exceed`
- [ ] **Task 1.2**: Create `entrypoint.sh` Docker-based action runner
- [ ] **Task 1.3**: Implement `src/ci/github_action_runner.py` — wraps Orchestrator for CI context
- [ ] **Task 1.4**: Output structured JSON result as GitHub Action output variables
- [ ] **Task 1.5**: Post a formatted PR comment with CLS score, friction points table, and screenshot thumbnails
- [ ] **Task 1.6**: Create `Dockerfile` for the action container (Python 3.11 + Playwright)
- [ ] **Task 1.7**: Write unit tests for the CI runner (mock GitHub API calls)
- [ ] **Task 1.8**: Create example workflow YAML in `examples/github-action-example.yml`
- [ ] **Task 1.9**: Submit PR

---

### 📋 `feature/m3-dynamic-persona` — Copilot

**Goal**: Integrate Google Analytics export data to dynamically generate Persona profiles based on real user demographics.

**目標**：整合 Google Analytics 匯出資料，根據真實用戶人口統計數據動態生成 Persona 畫像。

- [ ] **Task 2.1**: Define `GAPersonaConfig` Pydantic model (GA property ID, date range, segment filters)
- [ ] **Task 2.2**: Implement `GAPersonaGenerator` — reads GA4 export CSV/JSON and maps demographics to `PersonaProfile`
- [ ] **Task 2.3**: Implement persona clustering logic (group GA users into 3–5 representative archetypes)
- [ ] **Task 2.4**: Add `--from-ga` CLI flag to `src/main.py` to auto-generate personas from GA data
- [ ] **Task 2.5**: Create 3 sample GA export fixtures for testing (mock CSV files)
- [ ] **Task 2.6**: Write unit tests for `GAPersonaGenerator` (deterministic clustering)
- [ ] **Task 2.7**: Submit PR

---

### 📋 `feature/m3-saas-api` — Cursor

**Goal**: Build a FastAPI REST API layer with API key authentication, enabling self-serve access to the engine.

**目標**：建立一個帶有 API 金鑰認證的 FastAPI REST API 層，實現對引擎的自助式存取。

- [ ] **Task 3.1**: Create `src/api/app.py` — FastAPI application with CORS and error handlers
- [ ] **Task 3.2**: Implement `POST /v1/audits` endpoint — accepts scenario JSON, returns job ID
- [ ] **Task 3.3**: Implement `GET /v1/audits/{job_id}` endpoint — returns audit status and result
- [ ] **Task 3.4**: Implement `GET /v1/audits/{job_id}/report` endpoint — returns HTML report
- [ ] **Task 3.5**: Implement API key auth middleware (`X-API-Key` header)
- [ ] **Task 3.6**: Add background task queue (using `asyncio` or `BackgroundTasks`) for async audit runs
- [ ] **Task 3.7**: Create `src/api/models.py` — Pydantic request/response models
- [ ] **Task 3.8**: Write API integration tests using `httpx.AsyncClient`
- [ ] **Task 3.9**: Create `docs/API_V1.md` — OpenAPI-style endpoint documentation
- [ ] **Task 3.10**: Submit PR

---

### 📋 `feature/m3-benchmark-report` — Cursor

**Goal**: Build a batch runner that audits the top 50 e-commerce sites across **Hong Kong and Taiwan** and generates a bilingual, publishable benchmark report.

**目標**：建立一個批次執行器，對**香港及台灣**前 50 大電商網站進行審計，並生成可發布的雙語基準測試報告。

> **Scope Update**: Coverage expanded from Taiwan-only to **Hong Kong + Taiwan** (25 HK sites + 25 TW sites). Site list is pre-populated in `data/top50_hk_tw_ecommerce.json`. Three standard Personas are defined (Busy Mom HK, Tech Millennial TW, Senior Shopper HK).

- [ ] **Task 4.1**: Create `scripts/benchmark_runner.py` — batch scenario runner with rate limiting, retry, and region-aware persona selection
- [ ] **Task 4.2**: ~~Create data file~~ ✅ **DONE** — `data/top50_hk_tw_ecommerce.json` already created with 50 sites (25 HK + 25 TW), 3 benchmark flows, and 3 regional personas
- [ ] **Task 4.3**: Implement parallel audit execution (asyncio, max 3 concurrent, respects per-domain rate limits)
- [ ] **Task 4.4**: Implement `BenchmarkReportGenerator` — aggregates all audit results into a bilingual ranked HTML report (EN + 繁中)
- [ ] **Task 4.5**: Add region-split CLS distribution charts (HK vs TW side-by-side comparison, histogram per category)
- [ ] **Task 4.6**: Add "Hall of Shame" and "Hall of Fame" sections (top 5 worst / best CLS per region)
- [ ] **Task 4.7**: Add cross-region comparison summary table (avg CLS by category: Fashion, Electronics, Grocery, etc.)
- [ ] **Task 4.8**: Write unit tests for `BenchmarkReportGenerator` (mock audit results)
- [ ] **Task 4.9**: Submit PR

---

## 🔗 Module Interface Contracts

All agents MUST respect these interfaces. Do not change them without a PR discussion.

### PersonaEngine Interface
```python
class PersonaEngine:
    def get_system_prompt(self, profile: PersonaProfile) -> str: ...
    def get_cognitive_constraints(self, profile: PersonaProfile) -> dict: ...
    def decide_next_action(self, state: NavigationState, constraints: dict) -> dict: ...  # M2+
    def generate_from_ga(self, ga_config: GAPersonaConfig) -> list[PersonaProfile]: ...   # M3
```

### NavigationEngine Interface
```python
class NavigationEngine:
    def navigate_to(self, url: str) -> NavigationState: ...
    def perform_action(self, action: str, selector: str, value: str | None) -> NavigationState: ...
    def close(self) -> None: ...
```

### EvaluationEngine Interface
```python
class CognitiveEvaluationEngine:
    def evaluate_step(self, dom_state: NavigationState, persona_constraints: dict) -> StepEvaluationResult: ...
```

### ReportingEngine Interface
```python
class ReportingEngine:
    def generate(self, trace: dict, output_dir: str) -> str: ...  # returns report file path
```
