# Persona Friction Engine — Multi-Agent Cloud Collaboration Guide

Welcome, Agent! This repository is designed for fully automated, cloud-based multi-agent development. 
We operate under a **Schema-First**, **Mock-First**, and **CI-Enforced** workflow.

---

## 🚀 Current Milestone: Milestone 2 (M2) — Audit as a Service & LLM Vision
**Objective**: Transition from rule-based M1 mock evaluations to dynamic, LLM-powered visual and cognitive UX audits, with a polished HTML reporting interface.

### 👥 M2 Multi-Agent Assignments

We have divided the M2 scope into four parallel feature branches. Check out your assigned branch and complete your tasks:

| Branch | Assigned Agent | Core Focus |
| :--- | :--- | :--- |
| `feature/m2-persona-llm` | **GitHub Copilot** | LLM-based cognitive state & dynamic intent generation |
| `feature/m2-vision-eval` | **Cursor** | GPT-4o Vision visual complexity & interaction friction audit |
| `feature/m2-interactive-report` | **Cursor** | Interactive HTML reporting engine with timeline & CLS charts |
| `feature/m2-orchestrator-integration` | **Manus** | End-to-end integration, scenario runner CLI, and robust error recovery |

---

## 📋 Detailed Task Lists per Branch

### 1. `feature/m2-persona-llm` (Assigned: GitHub Copilot)
**Goal**: Upgrade `PersonaEngine` to dynamically update the persona's internal cognitive state, motivation, and choose the next action based on current DOM/screenshot.

- [ ] **Task 1.1: Dynamic State Model**
  - Extend `src/persona/models.py` to include `PersonaState` (tracks remaining patience, current motivation, confusion level, and execution history).
- [ ] **Task 1.2: LLM Action Decision**
  - Implement `PersonaEngine.decide_next_action(profile, state, dom_state, screenshot_path) -> dict` using OpenAI `gpt-4.1-mini` or `gemini-2.5-flash`.
  - The model must output a structured JSON containing: `action` (`click`/`fill`/`scroll`/`wait`/`dropout`), `selector` (target element), `value` (if filling), and `thought_process` (cognitive justification).
- [ ] **Task 1.3: Dynamic Prompting**
  - Inject persona biases (e.g., loss aversion, status quo bias) dynamically into the LLM decision prompt.
- [ ] **Task 1.4: Unit Tests**
  - Write tests in `tests/test_persona.py` using mock LLM responses to verify correct state updates and decision parsing.

---

### 2. `feature/m2-vision-eval` (Assigned: Cursor)
**Goal**: Upgrade `CognitiveEvaluationEngine` to use GPT-4o Vision (`gpt-4.1-mini` or equivalent multimodal model) to analyze page screenshots and evaluate visual complexity and interaction friction.

- [ ] **Task 2.1: Vision API Integration**
  - Implement `src/evaluation/engine.py` to support `use_llm=True` in `evaluate_step`.
  - Send the step screenshot and DOM elements to the LLM.
- [ ] **Task 2.2: Standardized Evaluation Schema**
  - Ensure the LLM returns structured JSON matching `schemas/step_evaluation.json`.
  - Strictly calculate **Cognitive Load Score (CLS)** using our deterministic 3D formula:
    $$\text{CLS} = 0.35 \times \text{VisualComplexity} + 0.40 \times \text{InteractionFriction} + 0.25 \times (100 - \text{CognitiveAlignment})$$
- [ ] **Task 2.3: Visual Friction Identification**
  - Ask the LLM to identify specific visual friction points (e.g., "poor contrast", "cluttered layout", "hidden CTA") with severity, coordinates, and recommendations.
- [ ] **Task 2.4: Unit Tests**
  - Write tests in `tests/test_evaluation.py` to verify schema validation and deterministic score calculations.

---

### 3. `feature/m2-interactive-report` (Assigned: Cursor)
**Goal**: Create a beautiful, interactive HTML/CSS dashboard for audit results, including a timeline of user steps, CLS score charts, and detailed friction points.

- [ ] **Task 3.1: Interactive Report Template**
  - Design a responsive HTML template in `src/reporting/engine.py` using Tailwind CSS (via CDN) and Chart.js (via CDN).
- [ ] **Task 3.2: Timeline & Chart Visualization**
  - Render a step-by-step timeline of the simulation.
  - Render a line chart showing CLS progression over steps, highlighting the dropout point if applicable.
- [ ] **Task 3.3: Friction Points Inspector**
  - Display a detailed list of identified friction points, color-coded by severity (Critical, High, Medium, Low), with recommendations.
  - If coordinates are available, overlay them on the step screenshot.
- [ ] **Task 3.4: Unit Tests**
  - Write tests to verify HTML file generation and ensure no external network dependencies are required for the template compilation.

---

### 4. `feature/m2-orchestrator-integration` (Assigned: Manus)
**Goal**: Connect all M2 modules together, handle screenshots properly in the main loop, implement robust error recovery, and update the CLI runner.

- [ ] **Task 4.1: Real Engine Integration**
  - Replace the M1 mock engines in `src/main.py` with real instances of `PersonaEngine`, `NavigationEngine`, `CognitiveEvaluationEngine`, and `ReportingEngine`.
- [ ] **Task 4.2: Main Loop Orchestration**
  - Ensure `Orchestrator.run_scenario` coordinates screenshot taking: `NavigationEngine` takes screenshot → `CognitiveEvaluationEngine` evaluates screenshot → `PersonaEngine` decides next action based on screenshot + evaluation.
- [ ] **Task 4.3: Error Recovery & Graceful Exit**
  - If Playwright fails or LLM rate limits are hit, gracefully save the partial trace and generate a partial report rather than crashing.
- [ ] **Task 4.4: End-to-End Integration Tests**
  - Create integration tests in `tests/test_integration.py` running a mock local server to test the entire pipeline.

---

## 🛠️ Developer Agent Collaboration Rules

1. **Schema-First**: All interface boundaries are defined by JSON Schemas in `schemas/`. Any changes to these schemas must be done via a separate PR to `main` before implementing the code.
2. **Mock-First**: When implementing your module, mock your dependencies. Do not wait for other agents to finish their branches.
3. **CI Enforced**: Every branch must pass all unit tests on every push. GitHub Actions will run `pytest` on all PRs.
4. **Pull Requests**:
   - Work on your assigned `feature/` branch.
   - When done, open a PR into `main`.
   - Ensure the PR title starts with `feat(...)` or `fix(...)`.
   - Wait for CI checks to pass before requesting a merge.

Let's build the ultimate Persona Friction Engine! 🚀
