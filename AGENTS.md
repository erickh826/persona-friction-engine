# Multi-Agent Collaborative Development Guide (AGENTS.md)

> This file is the **single source of truth** for all AI agents working on this repository.
> Read this file in full before writing any code. Every agent has a designated branch and a specific task list.
> Do not work outside your designated branch without creating a GitHub Issue first.

---

## Repository Overview

**Project**: Persona-Driven UX Friction Simulation Engine
**Architecture Reference**: [SYSTEM_SPEC.md](./SYSTEM_SPEC.md)
**API Contracts**: [docs/API.md](./docs/API.md)
**Current Milestone**: M1 — Core Spike Test & CLS Formula Validation (Weeks 1–10)

---

## Agent Assignments & Branch Map

| Agent | Branch | Module | Milestone |
| :--- | :--- | :--- | :--- |
| **Manus AI** | `feature/m1-orchestrator` | Orchestration Engine | M1 |
| **Cursor** | `feature/m1-navigation-engine` | Navigation Engine (Playwright) | M1 |
| **Cursor** | `feature/m1-evaluation-engine` | Cognitive Evaluation Engine (Rule-based CLS) | M1 |
| **GitHub Copilot** | `feature/m1-persona-engine` | Persona Engine | M1 |

---

## Branch Task Lists

---

### `feature/m1-persona-engine` — Assigned to: GitHub Copilot

**Module**: `src/persona/`
**Goal**: Build the Persona Engine that generates cognitive profiles and LLM system prompts for each simulated user.

#### Task List

- [ ] **Task 1.1 — Define `PersonaProfile` Pydantic model** in `src/persona/models.py`
  - Fields: `name` (str), `age` (int), `tech_savviness` (int 1–5), `attention_span_seconds` (int), `motivation_level` (int 1–5), `cognitive_biases` (List[str])
  - All fields must match the schema in `schemas/scenario.json` under the `persona` key.

- [ ] **Task 1.2 — Implement `PersonaEngine` class** in `src/persona/engine.py`
  - Method `get_system_prompt(profile: PersonaProfile) -> str`: Returns a detailed LLM system prompt instructing the model to behave as the persona. The prompt must include the persona's tech level, attention constraints, and motivation.
  - Method `get_cognitive_constraints(profile: PersonaProfile) -> dict`: Returns a dictionary with keys `max_steps` (derived from `attention_span_seconds / 30`), `complexity_tolerance` (derived from `tech_savviness`), and `dropout_threshold` (derived from `motivation_level`).

- [ ] **Task 1.3 — Create 3 static persona fixtures** in `src/persona/fixtures.py`
  - `PERSONA_BUSY_MOM`: age=38, tech_savviness=2, attention_span_seconds=45, motivation_level=3, cognitive_biases=["loss aversion", "status quo bias"]
  - `PERSONA_TECH_MILLENNIAL`: age=28, tech_savviness=5, attention_span_seconds=120, motivation_level=4, cognitive_biases=["social proof"]
  - `PERSONA_SENIOR_SHOPPER`: age=62, tech_savviness=1, attention_span_seconds=90, motivation_level=5, cognitive_biases=["authority bias", "anchoring"]

- [ ] **Task 1.4 — Write unit tests** in `tests/test_persona.py`
  - Test that `get_system_prompt` returns a non-empty string for each fixture.
  - Test that `get_cognitive_constraints` returns a dict with keys `max_steps`, `complexity_tolerance`, `dropout_threshold`.
  - Test that `max_steps` is always at least 1.

- [ ] **Task 1.5 — Submit PR** to `main` with all tests passing via CI.

---

### `feature/m1-navigation-engine` — Assigned to: Cursor

**Module**: `src/navigation/`
**Goal**: Build the Playwright-based navigation driver that controls a headless Chromium browser, captures DOM state, and takes screenshots at each step.

#### Task List

- [ ] **Task 2.1 — Implement `NavigationState` Pydantic model** in `src/navigation/models.py`
  - Fields: `current_url` (str), `dom_tree_json` (str — serialized DOM as JSON string), `screenshot_path` (str — path to saved PNG), `page_title` (str), `visible_text_sample` (str — first 500 chars of visible text)

- [ ] **Task 2.2 — Implement `NavigationEngine` class** in `src/navigation/engine.py`
  - Constructor: `__init__(self, headless: bool = True, screenshots_dir: str = "screenshots/")`
  - Method `navigate_to(self, url: str) -> NavigationState`: Opens URL in headless Chromium, waits for `networkidle`, captures full-page screenshot, extracts DOM tree as JSON, returns `NavigationState`.
  - Method `perform_action(self, action: str, selector: str, value: str = None) -> NavigationState`: Supports `action` values of `"click"`, `"fill"`, `"scroll"`. Returns updated `NavigationState` after action.
  - Method `close(self)`: Closes the browser context cleanly.

- [ ] **Task 2.3 — Implement DOM extraction helper** in `src/navigation/dom_extractor.py`
  - Function `extract_dom_summary(page) -> dict`: Returns a simplified DOM tree with only interactive elements (buttons, inputs, links, headings, images). Each element should include `tag`, `text`, `aria_label`, `href` (if applicable), and `bounding_box`.

- [ ] **Task 2.4 — Write unit tests** in `tests/test_navigation.py`
  - Use a local mock HTML file (create `tests/fixtures/mock_page.html`) to avoid external network calls.
  - Test that `navigate_to` returns a valid `NavigationState` with a non-empty `screenshot_path`.
  - Test that `perform_action("click", ...)` returns an updated URL or DOM state.

- [ ] **Task 2.5 — Submit PR** to `main` with all tests passing via CI.

---

### `feature/m1-evaluation-engine` — Assigned to: Cursor

**Module**: `src/evaluation/`
**Goal**: Build the rule-based Cognitive Load Score (CLS) engine that evaluates a page state and produces a deterministic friction score without calling any external LLM APIs.

#### Task List

- [ ] **Task 3.1 — Implement output models** in `src/evaluation/models.py`
  - `FrictionPoint`: fields `severity` (Literal["low","medium","high","critical"]), `description` (str), `recommendation` (str)
  - `StepEvaluationResult`: fields `visual_complexity_score` (int 1–100), `interaction_friction_score` (int 1–100), `cognitive_alignment_score` (int 1–100), `composite_cls` (int 1–100), `identified_friction_points` (List[FrictionPoint])
  - Output must be serializable and validate against `schemas/step_evaluation.json`.

- [ ] **Task 3.2 — Implement rule-based `CognitiveEvaluationEngine`** in `src/evaluation/engine.py`
  - Constructor: `__init__(self, use_llm: bool = False, api_key: str = None)` — for M1, `use_llm` is always `False`.
  - Method `evaluate_step(self, dom_state: dict, persona_constraints: dict) -> StepEvaluationResult`
    - **Visual Complexity Score**: Calculated from `len(dom_state["elements"])`. >50 elements = score 80+; 20–50 = 40–79; <20 = 10–39.
    - **Interaction Friction Score**: Count of elements with no `aria_label` or empty `text` as a ratio. Also penalize if no primary CTA button is found.
    - **Cognitive Alignment Score**: Compare `persona_constraints["complexity_tolerance"]` (1–5) against the visual complexity score. Low tolerance + high complexity = low alignment score.
    - **Composite CLS**: `(0.35 * visual_complexity) + (0.40 * interaction_friction) + (0.25 * (100 - cognitive_alignment))`
  - Method `identify_friction_points(self, dom_state: dict) -> List[FrictionPoint]`: Applies heuristic rules to flag issues (e.g., missing form labels, no visible CTA, excessive text blocks).

- [ ] **Task 3.3 — Write unit tests** in `tests/test_evaluation.py`
  - Test that a DOM state with 60 elements returns a `visual_complexity_score` >= 80.
  - Test that a DOM state with no CTA button returns at least one `FrictionPoint` with `severity="high"`.
  - Test that the `composite_cls` formula is deterministic (same input → same output every time).

- [ ] **Task 3.4 — Submit PR** to `main` with all tests passing via CI.

---

### `feature/m1-orchestrator` — Assigned to: Manus AI

**Module**: `src/orchestrator/`
**Goal**: Build the orchestration loop that ties all modules together, runs a full scenario end-to-end, and saves the execution trace.

#### Task List

- [ ] **Task 4.1 — Implement `ScenarioLoader`** in `src/orchestrator/loader.py`
  - Function `load_scenario(path: str) -> dict`: Reads a JSON file, validates it against `schemas/scenario.json`, and returns the parsed dict. Raises `ValidationError` on schema mismatch.

- [ ] **Task 4.2 — Implement `Orchestrator` class** in `src/orchestrator/orchestrator.py`
  - Constructor: `__init__(self, persona_engine, nav_engine, eval_engine, report_engine)`
  - Method `run_scenario(self, scenario_path: str) -> dict`: Executes the full simulation loop:
    1. Load and validate scenario JSON.
    2. Initialize persona profile and get system prompt + constraints.
    3. Navigate to `target_url`.
    4. For each step up to `max_steps`: evaluate current DOM state, record `StepEvaluationResult`, decide next action (click primary CTA or stop if `composite_cls > dropout_threshold`).
    5. Save full execution trace to `output/<scenario_id>_trace.json`.
    6. Return the aggregated trace dict.

- [ ] **Task 4.3 — Implement CLI entrypoint** in `src/main.py`
  - Command: `python src/main.py --scenario <path_to_scenario.json>`
  - Prints a summary table of step-by-step CLS scores to stdout.
  - Saves the HTML report to `output/<scenario_id>_report.html`.

- [ ] **Task 4.4 — Create a sample scenario fixture** in `tests/fixtures/sample_scenario.json`
  - Use `target_url` pointing to a real public e-commerce page (e.g., `https://shopee.tw`) for integration testing.

- [ ] **Task 4.5 — Write unit tests** in `tests/test_orchestrator.py`
  - Use mock `PersonaEngine`, `NavigationEngine`, and `CognitiveEvaluationEngine` to test the orchestration loop in isolation.
  - Test that `run_scenario` returns a dict with keys `scenario_id`, `steps`, `final_cls`.
  - Test that the loop stops early if `composite_cls > dropout_threshold`.

- [ ] **Task 4.6 — Submit PR** to `main` with all tests passing via CI.

---

## Collaboration Rules

**Rule 1 — Schema is Law**: All inter-module data must validate against `/schemas/`. Do not change schemas without opening a GitHub Issue tagged `schema-change`.

**Rule 2 — Mock Before Integrate**: If your module depends on another that is not yet merged, write a mock class in your own `tests/` directory. Do not wait for other agents.

**Rule 3 — PR to `main` Only**: Never push directly to `main`. All work goes through Pull Requests. The CI pipeline must pass before merging.

**Rule 4 — One Module Per Branch**: Do not modify files outside your designated `src/<module>/` directory. Cross-module changes require a separate PR.

**Rule 5 — Determinism First**: For M1, all scoring must be deterministic. No random seeds, no LLM calls. Same input must always produce the same CLS output.

---

## Environment Setup (Cloud-Only, No Local Install)

Open a Codespace directly from GitHub:

```
https://github.com/erickh826/persona-friction-engine
→ Code → Codespaces → New Codespace on main (or your feature branch)
```

The Codespace will auto-install Python 3.11, Playwright, and all dependencies. Run tests with:

```bash
pytest -s
```
