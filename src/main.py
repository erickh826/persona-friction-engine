#!/usr/bin/env python3
"""
Persona Friction Engine — CLI Entrypoint

Usage:
    python src/main.py --scenario <path_to_scenario.json>
    python src/main.py --scenario tests/fixtures/sample_scenario.json --output output/

This script loads a scenario, runs the full simulation loop using
available engine implementations (or mocks), and outputs a summary
table of step-by-step CLS scores to stdout.
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.orchestrator import Orchestrator, ScenarioLoader, ScenarioValidationError


# ─── Mock Engines (for M1 standalone usage) ────────────────────────────────────
# These mocks allow the CLI to run without the other modules being implemented.
# They will be replaced by real implementations as other agents complete their work.


class MockPersonaEngine:
    """Mock Persona Engine for M1 standalone testing."""

    def get_system_prompt(self, profile: dict) -> str:
        name = profile.get("name", "User")
        tech = profile.get("tech_savviness", 3)
        return (
            f"You are {name}, a user with tech savviness level {tech}/5. "
            f"You have limited patience and will abandon tasks that feel confusing."
        )

    def get_cognitive_constraints(self, profile: dict) -> dict:
        attention = profile.get("attention_span_seconds", 60)
        tech = profile.get("tech_savviness", 3)
        motivation = profile.get("motivation_level", 3)
        return {
            "max_steps": max(1, attention // 30),
            "complexity_tolerance": tech,
            "dropout_threshold": 50 + (motivation * 10),  # 60-100 range
        }


class MockNavigationEngine:
    """Mock Navigation Engine for M1 standalone testing."""

    def __init__(self):
        self._step = 0
        self._mock_elements = [
            {"tag": "h1", "text": "Welcome to Shop", "selector": "h1", "aria_label": ""},
            {"tag": "input", "text": "", "selector": "input[name='email']", "aria_label": "Email", "value": ""},
            {"tag": "input", "text": "", "selector": "input[name='password']", "aria_label": "Password", "value": ""},
            {"tag": "button", "text": "Continue", "selector": "button.cta", "aria_label": "Continue to checkout"},
            {"tag": "a", "text": "Terms of Service", "selector": "a.tos", "aria_label": "", "href": "/tos"},
            {"tag": "img", "text": "", "selector": "img.hero", "aria_label": "Hero banner"},
            {"tag": "p", "text": "Enter your details to proceed with checkout.", "selector": "p.desc", "aria_label": ""},
        ]

    def navigate_to(self, url: str) -> dict:
        self._step = 0
        return {
            "current_url": url,
            "page_title": "Mock E-Commerce Page",
            "dom_tree_json": json.dumps({"elements": self._mock_elements, "page_title": "Mock Page"}),
            "screenshot_path": "screenshots/mock_step_0.png",
            "elements": self._mock_elements,
            "last_action": "navigate",
        }

    def perform_action(self, action: str, selector: str, value: str = None) -> dict:
        self._step += 1
        # Simulate page transition after CTA click
        new_elements = [
            {"tag": "h2", "text": "Order Summary", "selector": "h2", "aria_label": ""},
            {"tag": "div", "text": "Total: $49.99", "selector": "div.total", "aria_label": "Order total"},
            {"tag": "button", "text": "Confirm Purchase", "selector": "button.confirm", "aria_label": "Confirm"},
            {"tag": "a", "text": "Back to cart", "selector": "a.back", "aria_label": "Go back"},
        ]
        return {
            "current_url": f"https://mock-shop.example.com/step/{self._step}",
            "page_title": f"Step {self._step}",
            "dom_tree_json": json.dumps({"elements": new_elements, "page_title": f"Step {self._step}"}),
            "screenshot_path": f"screenshots/mock_step_{self._step}.png",
            "elements": new_elements,
            "last_action": f"{action}:{selector}",
        }

    def close(self):
        pass


class MockEvaluationEngine:
    """Mock Evaluation Engine for M1 standalone testing."""

    def __init__(self):
        self._call_count = 0

    def evaluate_step(self, dom_state: dict, persona_constraints: dict) -> dict:
        self._call_count += 1
        elements = dom_state.get("elements", [])
        num_elements = len(elements)

        # Rule-based scoring
        if num_elements > 50:
            visual = 85
        elif num_elements > 20:
            visual = 55
        else:
            visual = 25 + num_elements * 2

        # Check for missing labels
        unlabeled = sum(
            1 for e in elements
            if e.get("tag") in ("button", "input", "a")
            and not e.get("aria_label")
            and not e.get("text")
        )
        interaction = min(100, 30 + unlabeled * 20)

        # Cognitive alignment
        tolerance = persona_constraints.get("complexity_tolerance", 3)
        alignment = max(10, 100 - (visual - tolerance * 15))

        # Composite CLS
        composite = round(0.35 * visual + 0.40 * interaction + 0.25 * (100 - alignment))

        # Friction points
        friction_points = []
        if unlabeled > 0:
            friction_points.append({
                "severity": "medium",
                "description": f"{unlabeled} interactive element(s) missing accessible labels.",
                "recommendation": "Add aria-label or visible text to all interactive elements.",
            })
        if num_elements > 30:
            friction_points.append({
                "severity": "low",
                "description": "Page has high element density which may overwhelm low-tech users.",
                "recommendation": "Consider progressive disclosure or simplifying the layout.",
            })

        return {
            "visual_complexity_score": visual,
            "interaction_friction_score": interaction,
            "cognitive_alignment_score": alignment,
            "composite_cls": composite,
            "identified_friction_points": friction_points,
        }


class MockReportingEngine:
    """Mock Reporting Engine for M1 — generates a minimal HTML report."""

    def generate_html_report(self, run_result: dict, output_path: str) -> str:
        steps_html = ""
        for step in run_result.get("steps", []):
            friction_list = "".join(
                f"<li><strong>[{fp['severity']}]</strong> {fp['description']}</li>"
                for fp in step.get("identified_friction_points", [])
            )
            steps_html += f"""
            <tr>
                <td>{step['step_number']}</td>
                <td>{step['current_url']}</td>
                <td>{step['composite_cls']}</td>
                <td>{step['visual_complexity_score']}</td>
                <td>{step['interaction_friction_score']}</td>
                <td>{step['cognitive_alignment_score']}</td>
                <td><ul>{friction_list}</ul></td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Friction Report: {run_result['scenario_id']}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; }}
        h1 {{ color: #1a1a2e; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #16213e; color: white; }}
        .summary {{ background: #f0f4f8; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
        .dropout {{ color: #e74c3c; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>UX Friction Report</h1>
    <div class="summary">
        <p><strong>Scenario:</strong> {run_result['scenario_id']}</p>
        <p><strong>Target URL:</strong> {run_result['target_url']}</p>
        <p><strong>Persona:</strong> {run_result['persona_name']}</p>
        <p><strong>Final CLS:</strong> {run_result['final_cls']}</p>
        <p><strong>Total Steps:</strong> {run_result['total_steps']}</p>
        <p class="{'dropout' if run_result['dropout'] else ''}">
            <strong>Dropout:</strong> {'Yes — ' + run_result['dropout_reason'] if run_result['dropout'] else 'No'}
        </p>
    </div>
    <table>
        <thead>
            <tr>
                <th>Step</th>
                <th>URL</th>
                <th>CLS</th>
                <th>Visual</th>
                <th>Friction</th>
                <th>Alignment</th>
                <th>Issues</th>
            </tr>
        </thead>
        <tbody>{steps_html}</tbody>
    </table>
</body>
</html>"""

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path


# ─── CLI ───────────────────────────────────────────────────────────────────────


def print_summary_table(result: dict) -> None:
    """Print a formatted summary table of the simulation results."""
    print("\n" + "=" * 80)
    print(f"  PERSONA FRICTION ENGINE — Simulation Report")
    print("=" * 80)
    print(f"  Scenario:   {result['scenario_id']}")
    print(f"  Target:     {result['target_url']}")
    print(f"  Persona:    {result['persona_name']}")
    print(f"  Final CLS:  {result['final_cls']}")
    print(f"  Steps:      {result['total_steps']}")
    print(f"  Dropout:    {'YES — ' + result['dropout_reason'] if result['dropout'] else 'No'}")
    print(f"  Duration:   {result['execution_time_seconds']}s")
    print("-" * 80)
    print(f"  {'Step':<5} {'URL':<40} {'CLS':<5} {'Visual':<8} {'Friction':<10} {'Align':<7}")
    print("-" * 80)

    for step in result["steps"]:
        url_short = step["current_url"][:38] + ".." if len(step["current_url"]) > 40 else step["current_url"]
        print(
            f"  {step['step_number']:<5} {url_short:<40} "
            f"{step['composite_cls']:<5} {step['visual_complexity_score']:<8} "
            f"{step['interaction_friction_score']:<10} {step['cognitive_alignment_score']:<7}"
        )

    print("=" * 80)

    # Print friction points
    all_friction = []
    for step in result["steps"]:
        for fp in step.get("identified_friction_points", []):
            all_friction.append((step["step_number"], fp))

    if all_friction:
        print(f"\n  Identified Friction Points ({len(all_friction)} total):")
        print("-" * 80)
        for step_num, fp in all_friction:
            print(f"  [Step {step_num}] [{fp['severity'].upper()}] {fp['description']}")
            print(f"           → {fp['recommendation']}")
        print("")


def main():
    parser = argparse.ArgumentParser(
        description="Persona Friction Engine — Run UX friction simulation scenarios.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scenario",
        required=True,
        help="Path to the scenario JSON file.",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Output directory for traces and reports (default: output/).",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip HTML report generation.",
    )

    args = parser.parse_args()

    # Initialize mock engines (will be replaced by real implementations)
    persona_eng = MockPersonaEngine()
    nav_eng = MockNavigationEngine()
    eval_eng = MockEvaluationEngine()
    report_eng = None if args.no_report else MockReportingEngine()

    # Create orchestrator
    orchestrator = Orchestrator(
        persona_engine=persona_eng,
        navigation_engine=nav_eng,
        evaluation_engine=eval_eng,
        reporting_engine=report_eng,
        output_dir=args.output,
    )

    # Run scenario
    try:
        result = orchestrator.run_scenario(args.scenario)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ScenarioValidationError as e:
        print(f"VALIDATION ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Print summary
    print_summary_table(result)

    # Print output paths
    trace_path = Path(args.output) / f"{result['scenario_id']}_trace.json"
    print(f"  Trace saved to: {trace_path}")
    if "report_path" in result:
        print(f"  Report saved to: {result['report_path']}")
    print("")


if __name__ == "__main__":
    main()
