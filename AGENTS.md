# Multi-Agent Collaborative Development Guide (AGENTS.md)

---

## Welcome, AI Developer Agents!

This repository is optimized for **pure cloud-based multi-agent collaborative development** using **Manus**, **Cursor**, **GitHub Copilot Workspace**, and other cloud-based IDE agents. Since this project is developed entirely in the cloud without local environments, this guide outlines the protocols, interfaces, and rules you must follow to avoid conflicts and keep the codebase clean.

---

## 1. Cloud Agent Ecosystem & Tooling

To maintain a zero-local setup, each agent has an assigned role and environment:

| Agent Tool | Primary Role | Access Method | Working Branch |
| :--- | :--- | :--- | :--- |
| **Manus AI** | Architect, Schema Guard, Orchestrator | GitHub API & Sandbox VM | `main` (via PRs), `feature/m1-orchestrator` |
| **Cursor (Cloud)** | Heavy feature implementation, Refactoring | Codespaces / SSH Remote | `feature/m1-navigation-engine`, `feature/m1-evaluation-engine` |
| **GitHub Copilot** | Inline assistance, Unit tests, Rapid prototyping | Copilot Chat & Workspace | `feature/m1-persona-engine` |

---

## 2. Strict Collaboration Protocols

### Rule 1: Schema-First Development
All communication between modules is governed by Pydantic-compatible JSON schemas located in `/schemas/`. 
* **Do not** modify `/schemas/` without creating an issue first.
* All data payloads must validate against `/schemas/scenario.json` and `/schemas/step_evaluation.json`.

### Rule 2: Mock-First Dependency Resolution
If your module depends on another module that is not yet completed:
* Use the mock implementations defined in the `tests/` or mock classes.
* Do not block your development waiting for another agent to merge.

### Rule 3: Branch & Pull Request Flow
* **Never push directly to `main`**. The `main` branch is protected.
* Work on your designated `feature/m1-<module-name>` branch.
* Submit a Pull Request (PR) to merge into `main`.
* The PR must pass the automated GitHub Actions CI pipeline (defined in `.github/workflows/ci.yml`) before it can be merged.

---

## 3. Environment Setup (No Local Install Needed)

You can spin up a fully configured cloud development environment instantly using **GitHub Codespaces**:

1. Open the repository on GitHub.
2. Click the green **Code** button, select the **Codespaces** tab, and click **Create codespace on main**.
3. The environment will automatically:
   * Install Python 3.11 and Node.js 20.
   * Install all dependencies from `requirements.txt`.
   * Install Playwright and headless Chromium dependencies.
   * Install VS Code extensions for Python and GitHub Copilot.

---

## 4. Running Tests & Verifying Compliance

Before submitting your PR, ensure your module passes all unit tests:

```bash
# Run all tests
pytest

# Run tests with output
pytest -s
```

If you add new configuration or output payloads, validate them programmatically:

```python
import json
from jsonschema import validate

with open("schemas/step_evaluation.json") as f:
    schema = json.load(f)

# Your output payload
data = { ... } 
validate(instance=data, schema=schema) # Should not raise ValidationError
```

---

## 5. Current Active Milestone (M1: Core Spike Test)

We are currently building **Milestone M1 (Weeks 1-10)**. Focus on completing the core interfaces with deterministic rule-based logic before integrating LLMs in M2. Refer to [SYSTEM_SPEC.md](./SYSTEM_SPEC.md) for full architectural details.

Let's build the future of persona-driven usability testing together!
