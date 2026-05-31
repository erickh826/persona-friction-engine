# API Contracts and Module Integration Guide

This document serves as the interface guide for autonomous developer agents working on the **Persona-Driven UX Friction Simulation Engine**.

---

## 1. Persona Engine Interface (`src/persona/`)

The Persona Engine is responsible for loading and generating cognitive parameters for personas.

### Python Interface
```python
from pydantic import BaseModel, Field
from typing import List

class PersonaProfile(BaseModel):
    name: str
    age: int
    tech_savviness: int = Field(..., ge=1, le=5)
    attention_span_seconds: int
    motivation_level: int = Field(..., ge=1, le=5)
    cognitive_biases: List[str] = []

class PersonaEngine:
    def get_system_prompt(self, profile: PersonaProfile) -> str:
        """Generates the LLM system prompt instructing it to act as the persona."""
        pass

    def get_cognitive_constraints(self, profile: PersonaProfile) -> dict:
        """Returns mathematical constraints representing attention thresholds."""
        pass
```

---

## 2. Navigation Engine Interface (`src/navigation/`)

The Navigation Engine controls Playwright to drive Chromium and extract state.

### Python Interface
```python
from pydantic import BaseModel
from typing import Tuple

class NavigationState(BaseModel):
    current_url: str
    dom_tree_json: str
    screenshot_bytes: bytes

class NavigationEngine:
    def __init__(self, headless: bool = True):
        pass

    def navigate_to(self, url: str) -> NavigationState:
        """Navigates to a target URL and captures DOM state and screenshot."""
        pass

    def perform_action(self, action: str, target_element_selector: str, value: str = None) -> NavigationState:
        """Performs click, fill, or scroll actions on the page."""
        pass
```

---

## 3. Cognitive Evaluation Engine Interface (`src/evaluation/`)

The Cognitive Evaluation Engine uses Vision LLMs or rule-based heuristics to compute the Cognitive Load Score (CLS).

### Python Interface
```python
from pydantic import BaseModel
from typing import List, Optional

class FrictionPoint(BaseModel):
    severity: str  # low, medium, high, critical
    description: str
    recommendation: str

class StepEvaluationResult(BaseModel):
    visual_complexity_score: int
    interaction_friction_score: int
    cognitive_alignment_score: int
    composite_cls: int
    identified_friction_points: List[FrictionPoint]

class CognitiveEvaluationEngine:
    def __init__(self, api_key: Optional[str] = None):
        pass

    def evaluate_step(self, screenshot: bytes, dom_state: str, system_prompt: str) -> StepEvaluationResult:
        """Analyzes page screenshot and DOM state under the persona constraints."""
        pass
```

---

## 4. Orchestration Engine Interface (`src/orchestrator/`)

The Orchestrator ties all components together in a sequential execution loop.

### Python Interface
```python
from pydantic import BaseModel
from typing import List

class ScenarioRunResult(BaseModel):
    scenario_id: str
    success: bool
    steps: List[dict]  # List of StepEvaluation outputs
    final_cls: float

class Orchestrator:
    def __init__(self, persona_eng, nav_eng, eval_eng, report_eng):
        self.persona_eng = persona_eng
        self.nav_eng = nav_eng
        self.eval_eng = eval_eng
        self.report_eng = report_eng

    def run_scenario(self, scenario_json_path: str) -> ScenarioRunResult:
        """Loads a scenario, initializes components, and executes the loop."""
        pass
```

---

## 5. Reporting Engine Interface (`src/reporting/`)

The Reporting Engine takes the execution trace and compiles a static HTML report.

### Python Interface
```python
class ReportingEngine:
    def generate_html_report(self, run_result: dict, output_path: str) -> str:
        """Compiles the trace JSON into an interactive static HTML page."""
        pass
```
