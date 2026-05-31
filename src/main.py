#!/usr/bin/env python3
"""
Persona Friction Engine — CLI Entrypoint (M2)

Usage:
    python src/main.py --scenario <path_to_scenario.json>
    python src/main.py --scenario tests/fixtures/sample_scenario.json --output output/ --use-llm
    python src/main.py --scenario tests/fixtures/sample_scenario.json --headless --no-report

This script loads a scenario, runs the full simulation loop using
real engine implementations, and outputs a summary table of step-by-step
CLS scores to stdout. Generates an HTML report by default.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to path for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.orchestrator import Orchestrator, ScenarioLoader, ScenarioValidationError
from src.persona.engine import PersonaEngine
from src.persona.models import PersonaProfile
from src.navigation.engine import NavigationEngine
from src.evaluation.engine import CognitiveEvaluationEngine


# ─── Reporting Engine (Inline M2 Implementation) ──────────────────────────────
# This will be replaced by the dedicated ReportingEngine from Cursor's branch
# once feature/m2-interactive-report is merged.


class ReportingEngine:
    """
    M2 Reporting Engine — Generates an interactive HTML report with
    Tailwind CSS and Chart.js for CLS visualization.
    """

    def generate_html_report(self, run_result: dict, output_path: str) -> str:
        """Generate an interactive HTML report from the simulation results."""
        steps = run_result.get("steps", [])

        # Prepare chart data
        step_numbers = [s["step_number"] for s in steps]
        cls_scores = [s["composite_cls"] for s in steps]
        visual_scores = [s["visual_complexity_score"] for s in steps]
        friction_scores = [s["interaction_friction_score"] for s in steps]
        alignment_scores = [s["cognitive_alignment_score"] for s in steps]

        # Prepare friction points HTML
        friction_html = ""
        for step in steps:
            for fp in step.get("identified_friction_points", []):
                severity = fp.get("severity", "low")
                color_map = {
                    "critical": "bg-red-100 border-red-500 text-red-700",
                    "high": "bg-orange-100 border-orange-500 text-orange-700",
                    "medium": "bg-yellow-100 border-yellow-500 text-yellow-700",
                    "low": "bg-blue-100 border-blue-500 text-blue-700",
                }
                color = color_map.get(severity, color_map["low"])
                friction_html += f"""
                <div class="border-l-4 p-4 mb-3 rounded {color}">
                    <div class="flex justify-between items-center">
                        <span class="font-bold uppercase text-xs">{severity}</span>
                        <span class="text-xs text-gray-500">Step {step['step_number']}</span>
                    </div>
                    <p class="mt-1 text-sm">{fp.get('description', '')}</p>
                    <p class="mt-1 text-xs italic">Recommendation: {fp.get('recommendation', '')}</p>
                </div>"""

        # Steps timeline HTML
        timeline_html = ""
        for step in steps:
            timeline_html += f"""
            <div class="flex items-start mb-4">
                <div class="flex-shrink-0 w-10 h-10 rounded-full bg-indigo-500 text-white flex items-center justify-center font-bold text-sm">
                    {step['step_number']}
                </div>
                <div class="ml-4 flex-1">
                    <p class="text-sm font-medium text-gray-800">{step.get('action_taken', 'navigate')}</p>
                    <p class="text-xs text-gray-500 truncate">{step.get('current_url', '')}</p>
                    <div class="mt-1 flex gap-3 text-xs">
                        <span class="px-2 py-0.5 bg-purple-100 rounded">CLS: {step['composite_cls']}</span>
                        <span class="px-2 py-0.5 bg-blue-100 rounded">Visual: {step['visual_complexity_score']}</span>
                        <span class="px-2 py-0.5 bg-orange-100 rounded">Friction: {step['interaction_friction_score']}</span>
                        <span class="px-2 py-0.5 bg-green-100 rounded">Align: {step['cognitive_alignment_score']}</span>
                    </div>
                </div>
            </div>"""

        dropout_badge = ""
        if run_result.get("dropout"):
            dropout_badge = f"""
            <div class="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p class="text-red-700 font-bold">Persona Dropped Out</p>
                <p class="text-red-600 text-sm">{run_result.get('dropout_reason', '')}</p>
            </div>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UX Friction Report: {run_result['scenario_id']}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="max-w-6xl mx-auto px-6 py-10">
        <!-- Header -->
        <div class="bg-white rounded-xl shadow-sm p-8 mb-8">
            <h1 class="text-3xl font-bold text-gray-900">UX Friction Audit Report</h1>
            <p class="text-gray-500 mt-2">Generated by Persona Friction Engine</p>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                <div class="bg-gray-50 rounded-lg p-4">
                    <p class="text-xs text-gray-500 uppercase">Scenario</p>
                    <p class="text-sm font-bold text-gray-800 mt-1">{run_result['scenario_id']}</p>
                </div>
                <div class="bg-gray-50 rounded-lg p-4">
                    <p class="text-xs text-gray-500 uppercase">Persona</p>
                    <p class="text-sm font-bold text-gray-800 mt-1">{run_result['persona_name']}</p>
                </div>
                <div class="bg-gray-50 rounded-lg p-4">
                    <p class="text-xs text-gray-500 uppercase">Final CLS</p>
                    <p class="text-2xl font-bold text-indigo-600 mt-1">{run_result['final_cls']}</p>
                </div>
                <div class="bg-gray-50 rounded-lg p-4">
                    <p class="text-xs text-gray-500 uppercase">Steps</p>
                    <p class="text-2xl font-bold text-gray-800 mt-1">{run_result['total_steps']}</p>
                </div>
            </div>
            {dropout_badge}
        </div>

        <!-- CLS Chart -->
        <div class="bg-white rounded-xl shadow-sm p-8 mb-8">
            <h2 class="text-xl font-bold text-gray-900 mb-4">Cognitive Load Score Progression</h2>
            <canvas id="clsChart" height="100"></canvas>
        </div>

        <!-- Two Column Layout -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Timeline -->
            <div class="bg-white rounded-xl shadow-sm p-8">
                <h2 class="text-xl font-bold text-gray-900 mb-4">Step Timeline</h2>
                {timeline_html}
            </div>

            <!-- Friction Points -->
            <div class="bg-white rounded-xl shadow-sm p-8">
                <h2 class="text-xl font-bold text-gray-900 mb-4">Identified Friction Points</h2>
                {friction_html if friction_html else '<p class="text-gray-400 text-sm">No friction points identified.</p>'}
            </div>
        </div>

        <!-- Footer -->
        <div class="mt-8 text-center text-xs text-gray-400">
            <p>Target: {run_result['target_url']} | Duration: {run_result['execution_time_seconds']}s | {run_result['timestamp']}</p>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('clsChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(step_numbers)},
                datasets: [
                    {{
                        label: 'Composite CLS',
                        data: {json.dumps(cls_scores)},
                        borderColor: 'rgb(79, 70, 229)',
                        backgroundColor: 'rgba(79, 70, 229, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.3,
                    }},
                    {{
                        label: 'Visual Complexity',
                        data: {json.dumps(visual_scores)},
                        borderColor: 'rgb(147, 51, 234)',
                        borderWidth: 1.5,
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.3,
                    }},
                    {{
                        label: 'Interaction Friction',
                        data: {json.dumps(friction_scores)},
                        borderColor: 'rgb(234, 88, 12)',
                        borderWidth: 1.5,
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.3,
                    }},
                    {{
                        label: 'Cognitive Alignment',
                        data: {json.dumps(alignment_scores)},
                        borderColor: 'rgb(22, 163, 74)',
                        borderWidth: 1.5,
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.3,
                    }},
                ],
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        title: {{ display: true, text: 'Score (0-100)' }},
                    }},
                    x: {{
                        title: {{ display: true, text: 'Step' }},
                    }},
                }},
                plugins: {{
                    legend: {{ position: 'bottom' }},
                }},
            }},
        }});
    </script>
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
    print(f"  PERSONA FRICTION ENGINE — Simulation Report (M2)")
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
            print(f"           -> {fp['recommendation']}")
        print("")


def main():
    parser = argparse.ArgumentParser(
        description="Persona Friction Engine — Run UX friction simulation scenarios (M2).",
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
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Enable LLM-based evaluation (requires OPENAI_API_KEY env var).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True).",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible mode (for debugging).",
    )

    args = parser.parse_args()

    headless = not args.no_headless

    # Initialize REAL engines
    persona_eng = PersonaEngine()
    nav_eng = NavigationEngine(headless=headless, screenshots_dir=f"{args.output}/screenshots")
    eval_eng = CognitiveEvaluationEngine(
        use_llm=args.use_llm,
        api_key=os.environ.get("OPENAI_API_KEY") if args.use_llm else None,
    )
    report_eng = None if args.no_report else ReportingEngine()

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
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)

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
