"""
Orchestrator — Coordinates the full simulation loop across all engine modules.

The Orchestrator ties together the Persona Engine, Navigation Engine,
Cognitive Evaluation Engine, and Reporting Engine into a sequential
execution pipeline that processes a scenario end-to-end.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from .loader import ScenarioLoader


# ─── Protocol Interfaces ───────────────────────────────────────────────────────
# These protocols define the minimal interface each engine must implement.
# During M1, mock implementations are used for engines not yet built.


class PersonaEngineProtocol(Protocol):
    """Interface for the Persona Engine module."""

    def get_system_prompt(self, profile: dict) -> str:
        ...

    def get_cognitive_constraints(self, profile: dict) -> dict:
        ...


class NavigationEngineProtocol(Protocol):
    """Interface for the Navigation Engine module."""

    def navigate_to(self, url: str) -> dict:
        ...

    def perform_action(self, action: str, selector: str, value: str = None) -> dict:
        ...

    def close(self) -> None:
        ...


class EvaluationEngineProtocol(Protocol):
    """Interface for the Cognitive Evaluation Engine module."""

    def evaluate_step(self, dom_state: dict, persona_constraints: dict) -> dict:
        ...


class ReportingEngineProtocol(Protocol):
    """Interface for the Reporting Engine module."""

    def generate_html_report(self, run_result: dict, output_path: str) -> str:
        ...


# ─── Orchestrator ──────────────────────────────────────────────────────────────


class Orchestrator:
    """
    Coordinates the full UX friction simulation loop.
    
    The orchestrator:
    1. Loads and validates the scenario JSON.
    2. Initializes persona profile and retrieves cognitive constraints.
    3. Navigates to the target URL.
    4. Iterates through steps: evaluates DOM state, records CLS scores,
       and decides whether to continue or stop (dropout).
    5. Saves the full execution trace to a JSON file.
    6. Optionally generates an HTML report.
    
    Usage:
        orchestrator = Orchestrator(persona_eng, nav_eng, eval_eng, report_eng)
        result = orchestrator.run_scenario("scenarios/checkout_flow.json")
    """

    def __init__(
        self,
        persona_engine: PersonaEngineProtocol,
        navigation_engine: NavigationEngineProtocol,
        evaluation_engine: EvaluationEngineProtocol,
        reporting_engine: Optional[ReportingEngineProtocol] = None,
        output_dir: str = "output",
    ):
        """
        Initialize the Orchestrator.
        
        Args:
            persona_engine: Instance implementing PersonaEngineProtocol.
            navigation_engine: Instance implementing NavigationEngineProtocol.
            evaluation_engine: Instance implementing EvaluationEngineProtocol.
            reporting_engine: Optional instance implementing ReportingEngineProtocol.
            output_dir: Directory to save execution traces and reports.
        """
        self.persona_engine = persona_engine
        self.navigation_engine = navigation_engine
        self.evaluation_engine = evaluation_engine
        self.reporting_engine = reporting_engine
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._loader = ScenarioLoader()

    def run_scenario(self, scenario_path: str) -> Dict[str, Any]:
        """
        Execute a full simulation scenario.
        
        Args:
            scenario_path: Path to the scenario JSON file.
            
        Returns:
            A dictionary containing:
                - scenario_id (str): The scenario identifier.
                - target_url (str): The URL that was tested.
                - persona_name (str): Name of the simulated persona.
                - steps (List[dict]): Step-by-step evaluation results.
                - final_cls (float): Average composite CLS across all steps.
                - total_steps (int): Number of steps executed.
                - dropout (bool): Whether the persona dropped out early.
                - dropout_reason (str): Reason for dropout if applicable.
                - execution_time_seconds (float): Total execution duration.
                - timestamp (str): ISO 8601 timestamp of the run.
        """
        start_time = time.time()

        # Step 1: Load and validate scenario
        scenario = self._loader.load(scenario_path)
        scenario_id = scenario["scenario_id"]
        target_url = scenario["target_url"]
        target_goal = scenario["target_goal"]
        persona_data = scenario["persona"]
        max_steps = scenario.get("max_steps", 10)

        # Step 2: Initialize persona
        system_prompt = self.persona_engine.get_system_prompt(persona_data)
        constraints = self.persona_engine.get_cognitive_constraints(persona_data)
        dropout_threshold = constraints.get("dropout_threshold", 80)

        # Step 3: Navigate to target URL
        nav_state = self.navigation_engine.navigate_to(target_url)

        # Step 4: Simulation loop
        steps: List[Dict[str, Any]] = []
        dropout = False
        dropout_reason = ""

        for step_num in range(1, max_steps + 1):
            # Extract DOM state from navigation
            dom_state = self._extract_dom_state(nav_state)

            # Evaluate current step
            evaluation = self.evaluation_engine.evaluate_step(
                dom_state=dom_state,
                persona_constraints=constraints,
            )

            # Build step record
            step_record = {
                "step_number": step_num,
                "current_url": nav_state.get("current_url", target_url),
                "action_taken": nav_state.get("last_action", "navigate"),
                "visual_complexity_score": evaluation.get("visual_complexity_score", 0),
                "interaction_friction_score": evaluation.get("interaction_friction_score", 0),
                "cognitive_alignment_score": evaluation.get("cognitive_alignment_score", 0),
                "composite_cls": evaluation.get("composite_cls", 0),
                "identified_friction_points": evaluation.get("identified_friction_points", []),
                "screenshot_path": nav_state.get("screenshot_path", ""),
            }
            steps.append(step_record)

            # Check dropout condition
            composite_cls = evaluation.get("composite_cls", 0)
            if composite_cls > dropout_threshold:
                dropout = True
                dropout_reason = (
                    f"Composite CLS ({composite_cls}) exceeded dropout threshold "
                    f"({dropout_threshold}) at step {step_num}."
                )
                break

            # Decide next action (simple heuristic: click primary CTA if found)
            next_action = self._decide_next_action(dom_state, step_num, max_steps)
            if next_action is None:
                # No more actions to take
                break

            # Perform next action
            nav_state = self.navigation_engine.perform_action(
                action=next_action["action"],
                selector=next_action["selector"],
                value=next_action.get("value"),
            )

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
        }

        # Step 6: Save execution trace
        trace_path = self.output_dir / f"{scenario_id}_trace.json"
        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Step 7: Generate HTML report (if reporting engine is available)
        if self.reporting_engine:
            report_path = str(self.output_dir / f"{scenario_id}_report.html")
            self.reporting_engine.generate_html_report(result, report_path)
            result["report_path"] = report_path

        # Clean up navigation engine
        try:
            self.navigation_engine.close()
        except Exception:
            pass

        return result

    def _extract_dom_state(self, nav_state: dict) -> dict:
        """
        Extract a standardized DOM state dictionary from the navigation state.
        
        Args:
            nav_state: Raw navigation state from NavigationEngine.
            
        Returns:
            Standardized DOM state dict with 'elements' list.
        """
        # If nav_state already has structured DOM data, use it
        if "dom_tree_json" in nav_state:
            dom_data = nav_state["dom_tree_json"]
            if isinstance(dom_data, str):
                try:
                    return json.loads(dom_data)
                except json.JSONDecodeError:
                    pass
            elif isinstance(dom_data, dict):
                return dom_data

        # Fallback: construct minimal DOM state
        return {
            "elements": nav_state.get("elements", []),
            "page_title": nav_state.get("page_title", ""),
            "visible_text_sample": nav_state.get("visible_text_sample", ""),
        }

    def _decide_next_action(
        self, dom_state: dict, current_step: int, max_steps: int
    ) -> Optional[Dict[str, str]]:
        """
        Decide the next action based on the current DOM state.
        
        Simple heuristic for M1:
        - Look for a primary CTA button (submit, checkout, continue, next).
        - If found, click it.
        - If not found and there are form inputs, fill the first empty one.
        - If nothing actionable, return None to end the loop.
        
        Args:
            dom_state: Current DOM state dictionary.
            current_step: Current step number.
            max_steps: Maximum allowed steps.
            
        Returns:
            Action dict with 'action', 'selector', and optional 'value',
            or None if no action is available.
        """
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
