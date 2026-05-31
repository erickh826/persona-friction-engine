# Persona-Driven UX Friction Simulation Engine (SYSTEM SPECIFICATION)

---

## 1. Executive Summary & Vision

The **Persona-Driven UX Friction Simulation Engine** is an innovative AI-agent-based usability testing framework designed to simulate user behavior, measure cognitive friction, and identify conversion drop-off points on digital interfaces. By leveraging specialized LLM agents representing distinct target audience personas, the system programmatically navigates web applications, analyzes visual elements, and generates a deterministic **Cognitive Load Score (CLS)**. 

Unlike traditional general-purpose usability tools or simple synthetic test suites, this engine models the cognitive load and emotional friction of specific user profiles, bridging the gap between quantitative analytics (such as Google Lighthouse [1]) and qualitative user testing (such as Hotjar or UserTesting).

This document outlines a robust, modular, and phased system architecture specifically designed for **multi-agent collaborative development**. By breaking the system into isolated modules with strict interface contracts, multiple AI developers (agents) can concurrently build, test, and integrate components with minimal merge conflicts or architectural drift.

---

## 2. Core Architecture & Multi-Agent Collaboration Model

To enable seamless multi-agent collaborative development, the engine is structured into five isolated modules. Each module has a defined boundary, input/output contracts, and a mock implementation path.

```
                  +---------------------------------------+
                  |           User Interface              |
                  |  (CLI / Static HTML Report Generator)  |
                  +-------------------+-------------------+
                                      |
                                      v
                  +-------------------+-------------------+
                  |        Orchestration Engine           |
                  |     (Coordinator / Flow Manager)      |
                  +---------+-------------------+---------+
                            |                   |
         +------------------+                   +------------------+
         v                                                         v
+--------+--------------+                                 +--------+--------------+
|   Persona Engine      |                                 |   Navigation Engine   |
| (Cognitive Profiles)  |                                 |  (Playwright Driver)  |
+--------+--------------+                                 +--------+--------------+
         |                                                         |
         +------------------+                   +------------------+
                            |                   |
                            v                   v
                  +---------+-------------------+---------+
                  |         Cognitive Evaluation          |
                  |          (LLM Vision / CLS)           |
                  +---------------------------------------+
```

### 2.1 Module Definitions & Interface Contracts

| Module Name | Responsibility | Primary Inputs | Primary Outputs | Mock Implementation Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **Persona Engine** | Manages cognitive profiles, attention spans, tech-savviness, and task motivations. | Persona Config JSON, Target Goal | System Prompt, Cognitive Constraints JSON | Return static persona profiles with hardcoded biases and cognitive thresholds. |
| **Navigation Engine** | Programmatically drives Chromium, extracts DOM state, and captures full-page/element screenshots. | Target URL, Action Sequence (click, input, scroll) | DOM Tree Snapshot, Visual Screenshots, Execution Log | Use a headless browser to load a local mock HTML page and return predefined element coordinates. |
| **Cognitive Evaluation** | Evaluates screenshots and DOM trees via LLM Vision; computes the Cognitive Load Score (CLS). | Element Screenshot, DOM Context, Persona Constraints | Friction Points, Step CLS (1-100), Visual Complexity Rating | Return randomized or rule-based scores based on element density and text length without calling LLM APIs. |
| **Orchestration Engine** | Coordinates the execution loop, handles state transitions, and manages agent memory. | Test Scenario JSON (Persona + Target URL + Task) | Execution Trace, Aggregated Step-by-Step Metrics | Sequential execution of mock modules with simulated step delays. |
| **Reporting Engine** | Compiles execution traces into highly polished, structured, static HTML reports. | Aggregated Metrics, Execution Trace JSON | Static HTML Report File, Chart.js Visualizations | Parse static JSON test outputs and generate HTML using predefined Jinja2 templates. |

### 2.2 Multi-Agent Collaborative Development Protocols

To ensure that multiple AI agents can work together without breaking the codebase, the following development rules must be strictly enforced:

* **Strict Interface Contracts**: All module boundaries must be defined using **Pydantic schemas** (for Python-based components) or **TypeScript interfaces** (for Node.js-based components). No agent is allowed to modify the shared `schemas/` directory without consensus.
* **Test-Driven Isolation**: Each module must contain its own unit tests under `tests/` utilizing mock inputs. Agents must ensure their assigned module achieves 100% test pass rates using mock dependencies before integration.
* **Independent Feature Branching**: Agents must work on separate feature branches (e.g., `feature/persona-engine`, `feature/navigation-driver`) and submit Pull Requests (PRs) targeting the `main` branch.
* **Automated CI Verification**: A GitHub Actions workflow must run unit tests and check API contract compliance on every PR submission.

---

## 3. Core Technical Specifications

### 3.1 Cognitive Load Score (CLS) Methodology

The Cognitive Load Score (CLS) is a deterministic metric designed to quantify the mental effort required by a specific persona to complete a step in a user flow. Unlike standard web performance scores, CLS incorporates user-centric cognitive limitations [2] [3].

The CLS is computed using a weighted formula across three dimensions:

$$\text{CLS} = w_1 \cdot \text{Visual Complexity} + w_2 \cdot \text{Interaction Friction} + w_3 \cdot \text{Cognitive Alignment}$$

Where:
* **Visual Complexity ($V_c$)**: Measures visual clutter, text density, and layout chaos using LLM Vision analysis of screenshots and DOM element counts.
* **Interaction Friction ($I_f$)**: Measures execution barriers such as input fields without validation, unclear CTAs, multi-step navigation, and layout shifts.
* **Cognitive Alignment ($C_a$)**: Measures how well the interface matches the persona's mental model, vocabulary, and technical competency.

#### Metric Weighting Matrix

| Metric Dimension | Weight | Primary Data Source | Key Indicators |
| :--- | :--- | :--- | :--- |
| **Visual Complexity ($V_c$)** | 35% | LLM Vision Analysis & DOM Node Count | Total DOM elements, image-to-text ratio, color contrast, typography readability. |
| **Interaction Friction ($I_f$)** | 40% | Playwright Execution Logs & Error Traces | Form validation errors, steps to complete, layout stability (CLS-like metrics) [1]. |
| **Cognitive Alignment ($C_a$)** | 25% | LLM Semantic Comparison | Match between button labels and persona vocabulary, readability level of instructions. |

### 3.2 System Data Flow & Schema Definitions

```
[Scenario JSON] -> (Orchestrator) 
                      |-> Query -> (Persona Engine) -> [Persona System Prompt]
                      |-> Navigate -> (Navigation Engine) -> [Screenshot + DOM State]
                      |-> Evaluate -> (Cognitive Eval) -> [Step Metrics & CLS]
                      |-> Save State -> (Orchestrator Memory)
                      |-> Compile -> (Reporting Engine) -> [Static HTML Report]
```

#### Core Scenario Schema (`schemas/scenario.json`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TestScenario",
  "type": "object",
  "properties": {
    "scenario_id": { "type": "string" },
    "target_url": { "type": "string", "format": "uri" },
    "target_goal": { "type": "string" },
    "persona": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "age": { "type": "integer" },
        "tech_savviness": { "type": "integer", "minimum": 1, "maximum": 5 },
        "attention_span_seconds": { "type": "integer" },
        "motivation_level": { "type": "integer", "minimum": 1, "maximum": 5 },
        "cognitive_biases": {
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "required": ["name", "tech_savviness", "attention_span_seconds", "motivation_level"]
    },
    "max_steps": { "type": "integer", "default": 10 }
  },
  "required": ["scenario_id", "target_url", "target_goal", "persona"]
}
```

#### Step Evaluation Output Schema (`schemas/step_evaluation.json`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "StepEvaluation",
  "type": "object",
  "properties": {
    "step_number": { "type": "integer" },
    "current_url": { "type": "string", "format": "uri" },
    "action_taken": { "type": "string" },
    "visual_complexity_score": { "type": "integer", "minimum": 1, "maximum": 100 },
    "interaction_friction_score": { "type": "integer", "minimum": 1, "maximum": 100 },
    "cognitive_alignment_score": { "type": "integer", "minimum": 1, "maximum": 100 },
    "composite_cls": { "type": "integer", "minimum": 1, "maximum": 100 },
    "identified_friction_points": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "severity": { "type": "string", "enum": ["low", "medium", "high", "critical"] },
          "description": { "type": "string" },
          "recommendation": { "type": "string" }
        },
        "required": ["severity", "description", "recommendation"]
      }
    },
    "screenshot_path": { "type": "string" }
  },
  "required": ["step_number", "current_url", "composite_cls", "identified_friction_points"]
}
```

---

## 4. Phased Development Roadmap (Milestones M1–M3)

To ensure rapid validation, cash-efficiency, and alignment with commercial traction, the development is divided into three distinct milestones.

```
+---------------------------------------------------------------------------------+
|                               MILESTONE M1                                      |
|  Duration: 10 Weeks | Goal: Spike Test Demo & CLS Formula Validation             |
|  Focus: Rule-based scoring, basic Playwright driver, 3x3 static persona matrix  |
+---------------------------------------+-----------------------------------------+
                                        |
                                        v
+---------------------------------------------------------------------------------+
|                               MILESTONE M2                                      |
|  Duration: 18 Weeks | Goal: Audit as a Service Launch                           |
|  Focus: LLM Vision integration, Scenario Generator, static HTML report template |
+---------------------------------------+-----------------------------------------+
                                        |
                                        v
+---------------------------------------------------------------------------------+
|                               MILESTONE M3                                      |
|  Duration: 24+ Weeks | Goal: Scale & CI/CD Integration                          |
|  Focus: GitHub Action plugin, dynamic Persona Engine, academic score validation |
+---------------------------------------------------------------------------------+
```

### 4.1 Milestone M1: Core Spike Test & CLS Formula Validation
* **Duration**: Weeks 1–10
* **Objective**: Build a working spike-test prototype that navigates a mock flow, evaluates elements using a rule-based deterministic scoring engine, and outputs raw execution traces.
* **Exit Criteria**: Working Spike Test Demo, CLS v1 Formula locked, and written confirmation from at least 2 Design Partners that mock reports provided actionable UI improvement recommendations.
* **Multi-Agent Tasks**:
  * **Agent 1 (Nav)**: Implement the core Playwright navigation driver.
  * **Agent 2 (Eval)**: Implement the rule-based Cognitive Evaluation Engine (no LLM calls yet, using DOM element counts, contrast algorithms, and text lengths).
  * **Agent 3 (Orch)**: Build the Orchestrator and CLI to run tests using static JSON scenarios.

### 4.2 Milestone M2: "Audit as a Service" Launch & LLM Integration
* **Duration**: Weeks 11–28 (18 Weeks)
* **Objective**: Integrate LLM Vision to evaluate complex UI components, implement a Scenario Generator with 5 core scenarios, and build a beautiful static HTML report generator to support the "Audit as a Service" commercial track.
* **Exit Criteria**: First 5 paid audit clients, confirmed Value Metric (Scenario Runs), and a dedicated Full-Time Equivalent (FTE) Engineer onboarded.
* **Multi-Agent Tasks**:
  * **Agent 1 (Vision)**: Integrate OpenAI GPT-4o Vision API to analyze visual complexity and screen layout.
  * **Agent 2 (Scenario)**: Implement the Scenario Generator (generating step-by-step user paths based on a 5-scenario template library).
  * **Agent 3 (Report)**: Build the Reporting Engine (parsing execution trace JSON into a highly polished, interactive static HTML report using Chart.js).

### 4.3 Milestone M3: Self-Serve SaaS & CI/CD Integration
* **Duration**: Weeks 29–53+ (24+ Weeks)
* **Objective**: Turn the engine into a continuous monitoring tool by building a CI/CD GitHub Action plugin, enabling dynamic Persona generation via GA integration, and publishing an academic whitepaper validating the Friction Score.
* **Exit Criteria**: Achieve $50k+ MRR, GitHub Action plugin live in the Marketplace, and a joint academic whitepaper published with a top HCI university research lab.
* **Multi-Agent Tasks**:
  * **Agent 1 (CI/CD)**: Develop the GitHub Action wrapper that runs the simulation on pull requests and blocks releases if CLS exceeds thresholds.
  * **Agent 2 (GA)**: Integrate Google Analytics API to dynamically construct persona distributions based on real-world demographic data.
  * **Agent 3 (Scale)**: Build a Multi-Agent coordination layer (simulating simultaneous buyer-seller or user-support interactions).

---

## 5. Directory Structure & Development Guide

The repository is structured to maximize modularity and enable multiple agents to work on isolated folders without conflicts.

```
persona-friction-engine/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated test & schema validation runner
├── schemas/
│   ├── scenario.json            # Scenario Input Schema
│   └── step_evaluation.json     # Step Output Schema
├── src/
│   ├── __init__.py
│   ├── main.py                  # CLI Entrypoint
│   ├── orchestrator/            # Module 4: Orchestration Loop
│   ├── persona/                 # Module 1: Persona Engine
│   ├── navigation/              # Module 2: Playwright Navigation Engine
│   ├── evaluation/              # Module 3: LLM Vision & CLS Scoring Engine
│   └── reporting/               # Module 5: Static HTML Report Generator
├── tests/
│   ├── test_orchestrator.py
│   ├── test_persona.py
│   ├── test_navigation.py
│   ├── test_evaluation.py
│   └── test_reporting.py
├── docs/
│   └── API.md                   # API Contract and Module Integration Guide
├── requirements.txt             # Python dependencies
├── README.md                    # Project overview & quickstart
└── SYSTEM_SPEC.md               # This specification document
```

### 5.1 Getting Started for Developer Agents

1. **Schema First**: Before writing any logic, review the JSON schemas in the `schemas/` directory. All module interfaces must conform to these definitions.
2. **Implement Mocks**: If your module depends on another module that is not yet built, use the mock classes defined in the `tests/` or `src/` modules.
3. **Run Unit Tests**: Ensure that your module tests pass cleanly:
   ```bash
   pytest tests/test_<your_module>.py
   ```
4. **API and Schema Validation**: Use the automated scripts to validate your JSON outputs against the schemas before submitting a pull request.

---

## 6. References

[1] [Lighthouse performance scoring - Chrome for Developers](https://developer.chrome.com/docs/lighthouse/performance/performance-scoring)  
[2] [Cognitive Friction Measurement: Interaction Assessment of Digital Interfaces](https://openaccess-api.cms-conferences.org/articles/download/978-1-958651-60-5_3)  
[3] [A critical analysis of cognitive load measurement methods for UX research - arXiv](https://arxiv.org/abs/2402.11820)  
[4] [UXAgent: An LLM-agent-based usability testing framework for web design - Amazon Science](https://www.amazon.science/publications/uxagent-an-llm-agent-based-usability-testing-framework-for-web-design)  
[5] [Top 5 AI Agent Simulation Platforms in 2025 - Maxim AI](https://www.getmaxim.ai/articles/top-5-ai-agent-simulation-platforms-in-2025/)  
[6] [Designing an Efficient B2B Sales Team Structure for SaaS - ContentPeter](https://contentpeter.com/blog/designing-efficient-b2b-sales-team-structure-saas)  
[7] [When and How to Make Your Startup's First Hire - ICanPitch](https://www.icanpitch.com/blog/startup-first-hire-guide)  
[8] [How to Hire Your First Engineer Without Slowing Down Your Startup - SeekLab](https://theseeklab.com/blog/how_to_hire_your_first_engineer)  
[9] [SaaS Pricing Models: The 2026 Guide to 6 Winning Strategies - Revenera](https://www.revenera.com/blog/software-monetization/saas-pricing-models-guide/)  
[10] [Founders' Guide to Burn and Runway January 2026 - Puzzle](https://puzzle.io/blog/founders-guide-burn-rate-runway)  
