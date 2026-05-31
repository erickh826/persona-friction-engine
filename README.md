# Persona-Driven UX Friction Simulation Engine

---

## Overview

The **Persona-Driven UX Friction Simulation Engine** is an AI-agent-based usability testing framework. It programmatically navigates web applications, simulates real user behavior based on target audience personas, and computes a deterministic **Cognitive Load Score (CLS)** to identify conversion friction and usability bottlenecks.

This repository is structured specifically for **multi-agent collaborative development**. It uses modular design principles, strict API schemas, and test-driven boundaries so that multiple autonomous AI developers can concurrently build out components.

---

## Core Architecture

The engine is divided into five modular subsystems:

1. **Persona Engine (`src/persona/`)**: Manages demographic and cognitive profiles.
2. **Navigation Engine (`src/navigation/`)**: Headless browser controller using Playwright.
3. **Cognitive Evaluation Engine (`src/evaluation/`)**: Vision LLM scorer computing CLS.
4. **Orchestration Engine (`src/orchestrator/`)**: Coordinates scenarios, runs the loop, and tracks state.
5. **Reporting Engine (`src/reporting/`)**: Generates beautiful, static HTML reports.

For a deep dive into the system design, scoring formulas, and schemas, please refer to the [SYSTEM_SPEC.md](./SYSTEM_SPEC.md).

---

## Multi-Agent Development Guide

This project is built using **Schema-First Development**. To collaborate:

1. **Check Schemas**: All data exchanged between modules must validate against the schemas in `schemas/`.
2. **Implement Unit Tests**: Add test cases under `tests/` and run them using `pytest`.
3. **Mock Dependencies**: Use mock classes for unfinished modules.
4. **Follow CI Workflows**: Ensure all PRs pass GitHub Actions verification.

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/erickh826/persona-friction-engine.git
   cd persona-friction-engine
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the tests:
   ```bash
   pytest
   ```

---

## Roadmap

* **Milestone M1 (Weeks 1-10)**: Core Spike Test, rule-based scoring, and static persona matrix.
* **Milestone M2 (Weeks 11-28)**: "Audit as a Service" Launch, LLM Vision integration, and interactive static HTML report templates.
* **Milestone M3 (Weeks 29-53+)**: CI/CD GitHub Action integration, Google Analytics dynamic personas, and academic Friction Score validation.

---

## License

This project is proprietary and confidential. All rights reserved.
