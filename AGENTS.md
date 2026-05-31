# AGENTS.md

Guidance for AI agents working in this repository.

## Cursor Cloud specific instructions

### Project shape

Single Python 3.11+ project (no monorepo, no long-running app server yet). The repo is a **schema-first scaffold**: JSON schemas in `schemas/`, empty module packages under `src/`, and unit tests in `tests/`. `src/main.py` and engine modules are planned but not implemented.

### Dependencies

- Install: `pip install -r requirements.txt` (see [README.md](./README.md) Quick Start).
- **Playwright browsers** are not installed by `pip`. After a fresh VM or cache wipe, run once: `playwright install chromium` (or `playwright install` for all browsers). Required when working on `src/navigation/`, not for schema-only `pytest` runs.

### PATH

`pip install --user` may place `pytest` and `playwright` in `~/.local/bin`. If commands are not found, use:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Lint / build

No lint formatter or type checker is configured yet (no ruff, flake8, mypy, or `pyproject.toml`). CI only runs tests.

### Test

From repo root:

```bash
pytest
```

Matches [.github/workflows/ci.yml](./.github/workflows/ci.yml) (CI installs `pytest`, `jsonschema`, `pydantic` explicitly; local dev should use full `requirements.txt`).

### Run / services

There is **no dev server** to start for the engine itself. Future E2E runs will need:

1. Python + Playwright Chromium (above)
2. A **target web app** URL (external site or a local static server you start for mock HTML)

Optional later: OpenAI Vision API (M2), Google Analytics API (M3).

### Module map

| Path | Role |
|------|------|
| `src/persona/` | Persona profiles |
| `src/navigation/` | Playwright driver |
| `src/evaluation/` | CLS scoring |
| `src/orchestrator/` | Scenario loop |
| `src/reporting/` | HTML reports |

Contracts: [docs/API.md](./docs/API.md), [SYSTEM_SPEC.md](./SYSTEM_SPEC.md).
