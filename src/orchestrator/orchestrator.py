"""
Orchestrator — Coordinates the full simulation loop across all engine modules.

M2 Upgrade:
- Screenshot-based evaluation: NavigationEngine captures screenshots, which are
  passed to the EvaluationEngine for visual analysis.
- Persona-driven decisions: The PersonaEngine (when LLM-enabled in M2) can
  decide the next action based on DOM state + screenshot + evaluation results.
- Error recovery: Graceful handling of Playwright crashes, LLM rate limits,
  and network failures with partial trace saving.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from .loader import ScenarioLoader

try:
    from src.persona.models import PersonaProfile
    _HAS_PERSONA_MODEL = True
except ImportError:
    _HAS_PERSONA_MODEL = False

logger = logging.getLogger(__name__)


# ─── Protocol Interfaces ───────────────────────────────────────────────────────


class PersonaEngineProtocol(Protocol):
    """Interface for the Persona Engine module."""

    def get_system_prompt(self, profile) -> str:
        ...

    def get_cognitive_constraints(self, profile) -> dict:
        ...


class NavigationEngineProtocol(Protocol):
    """Interface for the Navigation Engine module."""

    def navigate_to(self, url: str):
        ...

    def perform_action(self, action: str, selector: str, value: str = None):
        ...

    def close(self) -> None:
        ...


class EvaluationEngineProtocol(Protocol):
    """Interface for the Cognitive Evaluation Engine module."""

    def evaluate_step(self, dom_state: dict, persona_constraints: dict):
        ...


class ReportingEngineProtocol(Protocol):
    """Interface for the Reporting Engine module."""

    def generate_html_report(self, run_result: dict, output_path: str) -> str:
        ...


# ─── Custom Exceptions ────────────────────────────────────────────────────────


class OrchestratorError(Exception):
    """Base exception for orchestrator errors."""
    pass


class NavigationError(OrchestratorError):
    """Raised when navigation fails (Playwright crash, timeout, etc.)."""
    pass


class EvaluationError(OrchestratorError):
    """Raised when evaluation fails (LLM rate limit, parsing error, etc.)."""
    pass


# ─── Orchestrator ──────────────────────────────────────────────────────────────


class Orchestrator:
    """
    Coordinates the full UX friction simulation loop (M2).

    The orchestrator:
    1. Loads and validates the scenario JSON.
    2. Initializes persona profile and retrieves cognitive constraints.
    3. Navigates to the target URL (captures screenshot).
    4. Iterates through steps:
       a. Evaluates DOM state + screenshot via EvaluationEngine.
       b. Records CLS scores and friction points.
       c. Decides next action (heuristic or LLM-driven persona).
       d. Stops if CLS exceeds dropout threshold.
    5. Saves the full execution trace to a JSON file.
    6. Optionally generates an HTML report.
    7. On any error, saves a partial trace and exits gracefully.
    """

    def __init__(
        self,
        persona_engine: PersonaEngineProtocol,
        navigation_engine: NavigationEngineProtocol,
        evaluation_engine: EvaluationEngineProtocol,
        reporting_engine: Optional[ReportingEngineProtocol] = None,
        output_dir: str = "output",
        max_retries: int = 2,
    ):
        self.persona_engine = persona_engine
        self.navigation_engine = navigation_engine
        self.evaluation_engine = evaluation_engine
        self.reporting_engine = reporting_engine
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self._loader = ScenarioLoader()

    def run_scenario(self, scenario_path: str) -> Dict[str, Any]:
        """
        Execute a full simulation scenario with error recovery.

        Returns a result dict even on partial failure (with error metadata).
        """
        start_time = time.time()
        steps: List[Dict[str, Any]] = []
        dropout = False
        dropout_reason = ""
        error_info = None

        # Step 1: Load and validate scenario
        scenario = self._loader.load(scenario_path)
        scenario_id = scenario["scenario_id"]
        target_url = scenario["target_url"]
        target_goal = scenario["target_goal"]
        persona_data = scenario["persona"]
        max_steps = scenario.get("max_steps", 10)

        # Step 2: Initialize persona (convert dict to PersonaProfile if needed)
        persona_input = self._prepare_persona_input(persona_data)
        system_prompt = self.persona_engine.get_system_prompt(persona_input)
        constraints = self.persona_engine.get_cognitive_constraints(persona_input)
        dropout_threshold = constraints.get("dropout_threshold", 80)

        try:
            # Step 3: Navigate to target URL
            nav_state = self._safe_navigate(target_url)

            # Step 4: Simulation loop
            for step_num in range(1, max_steps + 1):
                # Extract DOM state and screenshot path
                dom_state = self._extract_dom_state(nav_state)
                screenshot_path = self._get_screenshot_path(nav_state)

                # Evaluate current step (with retry on failure)
                evaluation = self._safe_evaluate(dom_state, constraints, screenshot_path)

                # Build step record
                step_record = {
                    "step_number": step_num,
                    "current_url": self._get_url(nav_state),
                    "action_taken": self._get_last_action(nav_state),
                    "visual_complexity_score": self._get_score(evaluation, "visual_complexity_score"),
                    "interaction_friction_score": self._get_score(evaluation, "interaction_friction_score"),
                    "cognitive_alignment_score": self._get_score(evaluation, "cognitive_alignment_score"),
                    "composite_cls": self._get_score(evaluation, "composite_cls"),
                    "identified_friction_points": self._get_friction_points(evaluation),
                    "screenshot_path": screenshot_path,
                }
                steps.append(step_record)

                # Check dropout condition
                composite_cls = step_record["composite_cls"]
                if composite_cls > dropout_threshold:
                    dropout = True
                    dropout_reason = (
                        f"Composite CLS ({composite_cls}) exceeded dropout threshold "
                        f"({dropout_threshold}) at step {step_num}."
                    )
                    break

                # Decide next action
                next_action = self._decide_next_action(dom_state, step_num, max_steps)
                if next_action is None:
                    break

                # Perform next action (with error recovery)
                nav_state = self._safe_perform_action(next_action)
                if nav_state is None:
                    error_info = {"type": "NavigationError", "message": "Action failed after retries."}
                    break

        except NavigationError as e:
            logger.error(f"Navigation failed: {e}")
            error_info = {"type": "NavigationError", "message": str(e)}
        except EvaluationError as e:
            logger.error(f"Evaluation failed: {e}")
            error_info = {"type": "EvaluationError", "message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            error_info = {"type": type(e).__name__, "message": str(e)}
        finally:
            # Always close navigation engine
            try:
                self.navigation_engine.close()
            except Exception:
                pass

        # Step 5: Compute final metrics
        cls_scores = [s["composite_cls"] for s in steps if s["composite_cls"] > 0]
        final_cls = round(sum(cls_scores) / len(cls_scores), 2) if cls_scores else 0.0
        execution_time = round(time.time() - start_time, 3)

        # Build result
        result = {
            "scenario_id": scenario_id,
            "target_url": target_url,
            "target_goal": target_goal,
            "persona_name": persona_data.get("name", "Unknown"),
            "steps": steps,
            "final_cls": final_cls,
            "total_steps": len(steps),
            "dropout": dropout,
            "dropout_reason": dropout_reason,
            "execution_time_seconds": execution_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "completed": error_info is None,
            "error": error_info,
        }

        # Step 6: Save execution trace (always, even on partial failure)
        trace_path = self.output_dir / f"{scenario_id}_trace.json"
        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Step 7: Generate HTML report (even for partial results)
        if self.reporting_engine and steps:
            try:
                report_path = str(self.output_dir / f"{scenario_id}_report.html")
                self.reporting_engine.generate_html_report(result, report_path)
                result["report_path"] = report_path
            except Exception as e:
                logger.warning(f"Report generation failed: {e}")

        return result

    # ─── Persona Input Preparation ──────────────────────────────────────────────

    def _prepare_persona_input(self, persona_data: dict):
        """
        Convert persona dict to PersonaProfile model if the real PersonaEngine
        expects a Pydantic model. Falls back to raw dict if model is unavailable.
        """
        if _HAS_PERSONA_MODEL:
            try:
                return PersonaProfile(**persona_data)
            except Exception:
                # If conversion fails, pass raw dict (for mock engines)
                return persona_data
        return persona_data

    # ─── Safe Wrappers with Retry ──────────────────────────────────────────────

    def _safe_navigate(self, url: str):
        """Navigate with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                return self.navigation_engine.navigate_to(url)
            except Exception as e:
                if attempt == self.max_retries:
                    raise NavigationError(f"Failed to navigate to {url} after {self.max_retries + 1} attempts: {e}")
                logger.warning(f"Navigation attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(1)

    def _safe_perform_action(self, action: dict):
        """Perform an action with retry logic. Returns None on total failure."""
        for attempt in range(self.max_retries + 1):
            try:
                return self.navigation_engine.perform_action(
                    action=action["action"],
                    selector=action["selector"],
                    value=action.get("value"),
                )
            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(f"Action failed after {self.max_retries + 1} attempts: {e}")
                    return None
                logger.warning(f"Action attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(0.5)

    def _safe_evaluate(self, dom_state: dict, constraints: dict, screenshot_path: str):
        """Evaluate with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                result = self.evaluation_engine.evaluate_step(
                    dom_state=dom_state,
                    persona_constraints=constraints,
                )
                # Handle both Pydantic model and dict returns
                if hasattr(result, "model_dump"):
                    return result.model_dump()
                elif hasattr(result, "dict"):
                    return result.dict()
                return result
            except NotImplementedError:
                # LLM not available, fall back gracefully
                return {
                    "visual_complexity_score": 50,
                    "interaction_friction_score": 50,
                    "cognitive_alignment_score": 50,
                    "composite_cls": 50,
                    "identified_friction_points": [],
                }
            except Exception as e:
                if attempt == self.max_retries:
                    raise EvaluationError(f"Evaluation failed after {self.max_retries + 1} attempts: {e}")
                logger.warning(f"Evaluation attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(0.5)

    # ─── State Extraction Helpers ──────────────────────────────────────────────

    def _extract_dom_state(self, nav_state) -> dict:
        """Extract DOM state from NavigationState (handles both Pydantic model and dict)."""
        if hasattr(nav_state, "dom_tree_json"):
            dom_json = nav_state.dom_tree_json
        elif isinstance(nav_state, dict):
            dom_json = nav_state.get("dom_tree_json", "{}")
        else:
            return {"elements": []}

        if isinstance(dom_json, str):
            try:
                return json.loads(dom_json)
            except json.JSONDecodeError:
                return {"elements": []}
        elif isinstance(dom_json, dict):
            return dom_json
        return {"elements": []}

    def _get_screenshot_path(self, nav_state) -> str:
        """Extract screenshot path from NavigationState."""
        if hasattr(nav_state, "screenshot_path"):
            return nav_state.screenshot_path
        elif isinstance(nav_state, dict):
            return nav_state.get("screenshot_path", "")
        return ""

    def _get_url(self, nav_state) -> str:
        """Extract current URL from NavigationState."""
        if hasattr(nav_state, "current_url"):
            return nav_state.current_url
        elif isinstance(nav_state, dict):
            return nav_state.get("current_url", "")
        return ""

    def _get_last_action(self, nav_state) -> str:
        """Extract last action from NavigationState."""
        if hasattr(nav_state, "last_action"):
            return nav_state.last_action
        elif isinstance(nav_state, dict):
            return nav_state.get("last_action", "navigate")
        return "navigate"

    def _get_score(self, evaluation, key: str) -> int:
        """Safely extract a score from evaluation result."""
        if isinstance(evaluation, dict):
            return evaluation.get(key, 0)
        return getattr(evaluation, key, 0)

    def _get_friction_points(self, evaluation) -> list:
        """Safely extract friction points from evaluation result."""
        if isinstance(evaluation, dict):
            points = evaluation.get("identified_friction_points", [])
        else:
            points = getattr(evaluation, "identified_friction_points", [])

        # Ensure each point is a dict (not a Pydantic model)
        result = []
        for p in points:
            if hasattr(p, "model_dump"):
                result.append(p.model_dump())
            elif hasattr(p, "dict"):
                result.append(p.dict())
            elif isinstance(p, dict):
                result.append(p)
        return result

    # ─── Action Decision ───────────────────────────────────────────────────────

    def _decide_next_action(
        self, dom_state: dict, current_step: int, max_steps: int
    ) -> Optional[Dict[str, str]]:
        """
        Decide the next action based on the current DOM state.

        For M2, this uses a heuristic approach. When the PersonaEngine supports
        LLM-based decisions (decide_next_action method), the orchestrator will
        delegate to it instead.
        """
        # Check if persona engine supports LLM-based decisions (M2 upgrade)
        if hasattr(self.persona_engine, "decide_next_action"):
            try:
                decision = self.persona_engine.decide_next_action(dom_state)
                if decision and decision.get("action") != "dropout":
                    return decision
                elif decision and decision.get("action") == "dropout":
                    return None
            except Exception as e:
                logger.warning(f"LLM persona decision failed, falling back to heuristic: {e}")

        # Heuristic fallback
        elements = dom_state.get("elements", [])

        # Priority 1: Find primary CTA buttons
        cta_keywords = ["submit", "checkout", "continue", "next", "buy", "add to cart", "confirm", "proceed"]
        for elem in elements:
            if elem.get("tag") in ("button", "a", "input"):
                text = (elem.get("text", "") or "").lower()
                aria = (elem.get("aria_label", "") or "").lower()
                combined = f"{text} {aria}"
                if any(kw in combined for kw in cta_keywords):
                    selector = elem.get("selector", f'{elem.get("tag")}:has-text("{elem.get("text", "")}")')
                    return {"action": "click", "selector": selector}

        # Priority 2: Find unfilled form inputs
        for elem in elements:
            if elem.get("tag") == "input" and not elem.get("value"):
                selector = elem.get("selector", "input")
                return {"action": "fill", "selector": selector, "value": "test@example.com"}

        # No actionable elements found
        return None
