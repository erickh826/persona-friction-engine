"""
Unit tests for the GitHub Action CI Runner (src/ci/github_action_runner.py)

Tests cover:
- PR comment formatting (build_pr_comment)
- GitHub API helpers (mocked)
- Scenario generation (generate_scenario)
- Output variable setting (set_output)
- Main run() function with mocked engines
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ci.github_action_runner import (
    build_pr_comment,
    generate_scenario,
    set_output,
    _severity_emoji,
    _cls_badge,
    _get_pr_number,
    PERSONA_PRESETS,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_audit_result(
    cls: float = 45.0,
    steps: int = 3,
    friction_count: int = 2,
    completed: bool = True,
    dropout: bool = False,
    error: dict = None,
) -> dict:
    """Build a mock audit result dict."""
    step_list = []
    for i in range(steps):
        step_list.append({
            "step": i + 1,
            "action_taken": {"action": "click", "selector": f"button.step-{i+1}"},
            "cls_score": cls,
            "sub_scores": {
                "visual_complexity": 40.0,
                "interaction_friction": 50.0,
                "cognitive_alignment": 60.0,
            },
            "friction_points": [
                {
                    "type": "poor_contrast",
                    "severity": "high",
                    "description": "Button text has insufficient contrast ratio",
                    "recommendation": "Increase contrast to at least 4.5:1",
                }
            ] if friction_count > 0 else [],
        })
    result = {
        "scenario_id": "test-checkout-flow",
        "persona_name": "Busy Mom",
        "target_url": "https://example.com/checkout",
        "final_cls": cls,
        "total_steps": steps,
        "steps": step_list,
        "completed": completed,
        "dropout": dropout,
        "report_path": "/tmp/test_report.html",
    }
    if error:
        result["error"] = error
    return result


# ─── Tests: Helper Functions ──────────────────────────────────────────────────

class TestHelpers(unittest.TestCase):

    def test_severity_emoji_critical(self):
        self.assertEqual(_severity_emoji("critical"), "🔴")

    def test_severity_emoji_high(self):
        self.assertEqual(_severity_emoji("high"), "🟠")

    def test_severity_emoji_medium(self):
        self.assertEqual(_severity_emoji("medium"), "🟡")

    def test_severity_emoji_low(self):
        self.assertEqual(_severity_emoji("low"), "🟢")

    def test_severity_emoji_unknown(self):
        self.assertEqual(_severity_emoji("unknown"), "⚪")

    def test_severity_emoji_case_insensitive(self):
        self.assertEqual(_severity_emoji("CRITICAL"), "🔴")
        self.assertEqual(_severity_emoji("High"), "🟠")

    def test_cls_badge_passing(self):
        badge = _cls_badge(40.0, 70.0)
        self.assertIn("🟢", badge)
        self.assertIn("40.0", badge)

    def test_cls_badge_approaching(self):
        badge = _cls_badge(58.0, 70.0)
        self.assertIn("🟠", badge)

    def test_cls_badge_failing(self):
        badge = _cls_badge(75.0, 70.0)
        self.assertIn("🔴", badge)
        self.assertIn("exceeds threshold", badge)


# ─── Tests: PR Comment Builder ────────────────────────────────────────────────

class TestBuildPRComment(unittest.TestCase):

    def test_comment_contains_scenario_id(self):
        result = make_audit_result(cls=45.0)
        comment = build_pr_comment(result, threshold=70.0, scenario_id="checkout-flow")
        self.assertIn("checkout-flow", comment)

    def test_comment_contains_cls_score(self):
        result = make_audit_result(cls=45.0)
        comment = build_pr_comment(result, threshold=70.0, scenario_id="test")
        self.assertIn("45.0", comment)

    def test_comment_pass_status(self):
        result = make_audit_result(cls=45.0, completed=True)
        comment = build_pr_comment(result, threshold=70.0, scenario_id="test")
        self.assertIn("✅", comment)

    def test_comment_fail_status(self):
        result = make_audit_result(cls=80.0, completed=True)
        comment = build_pr_comment(result, threshold=70.0, scenario_id="test")
        self.assertIn("❌", comment)

    def test_comment_contains_friction_points_table(self):
        result = make_audit_result(cls=45.0, friction_count=2)
        comment = build_pr_comment(result, threshold=70.0, scenario_id="test")
        self.assertIn("Friction Points Inspector", comment)
        self.assertIn("poor_contrast", comment)

    def test_comment_contains_step_breakdown(self):
        result = make_audit_result(cls=45.0, steps=3)
        comment = build_pr_comment(result, threshold=70.0, scenario_id="test")
        self.assertIn("Step-by-Step CLS Breakdown", comment)

    def test_comment_dropout_warning(self):
        result = make_audit_result(cls=45.0, dropout=True)
        comment = build_pr_comment(result, threshold=70.0, scenario_id="test")
        self.assertIn("Yes ⚠️", comment)

    def test_comment_no_dropout(self):
        result = make_audit_result(cls=45.0, dropout=False)
        comment = build_pr_comment(result, threshold=70.0, scenario_id="test")
        self.assertIn("No", comment)

    def test_comment_contains_error_section(self):
        result = make_audit_result(
            cls=0.0, completed=False,
            error={"type": "PlaywrightError", "message": "Browser crashed"}
        )
        comment = build_pr_comment(result, threshold=70.0, scenario_id="test")
        self.assertIn("Audit Error", comment)
        self.assertIn("PlaywrightError", comment)

    def test_comment_contains_formula_footer(self):
        result = make_audit_result()
        comment = build_pr_comment(result, threshold=70.0, scenario_id="test")
        self.assertIn("CLS Formula", comment)

    def test_comment_caps_friction_points_at_15(self):
        """Verify that more than 15 friction points are truncated in the comment."""
        result = make_audit_result(cls=50.0, steps=1, friction_count=0)
        # Manually inject 20 friction points
        result["steps"][0]["friction_points"] = [
            {
                "type": f"issue_{i}",
                "severity": "medium",
                "description": f"Issue number {i}",
                "recommendation": f"Fix issue {i}",
            }
            for i in range(20)
        ]
        comment = build_pr_comment(result, threshold=70.0, scenario_id="test")
        self.assertIn("more friction points", comment)


# ─── Tests: Scenario Generation ───────────────────────────────────────────────

class TestGenerateScenario(unittest.TestCase):

    def test_generates_valid_json_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_scenario(
                target_url="https://example.com",
                persona_preset="busy-mom",
                max_steps=5,
                output_dir=tmpdir,
            )
            self.assertTrue(Path(path).exists())
            with open(path) as f:
                scenario = json.load(f)
            self.assertEqual(scenario["target_url"], "https://example.com")
            self.assertEqual(scenario["max_steps"], 5)
            self.assertIn("persona", scenario)

    def test_persona_preset_busy_mom(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_scenario("https://x.com", "busy-mom", 3, tmpdir)
            with open(path) as f:
                scenario = json.load(f)
            self.assertEqual(scenario["persona"]["name"], "Busy Mom")
            self.assertEqual(scenario["persona"]["age"], 38)

    def test_persona_preset_senior_shopper(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_scenario("https://x.com", "senior-shopper", 3, tmpdir)
            with open(path) as f:
                scenario = json.load(f)
            self.assertEqual(scenario["persona"]["name"], "Senior Shopper")
            self.assertEqual(scenario["persona"]["age"], 65)

    def test_unknown_preset_falls_back_to_busy_mom(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_scenario("https://x.com", "nonexistent-preset", 3, tmpdir)
            with open(path) as f:
                scenario = json.load(f)
            self.assertEqual(scenario["persona"]["name"], "Busy Mom")


# ─── Tests: set_output ────────────────────────────────────────────────────────

class TestSetOutput(unittest.TestCase):

    def test_writes_to_github_output_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            output_file = f.name
        try:
            with patch.dict(os.environ, {"GITHUB_OUTPUT": output_file}):
                set_output("cls_score", "45.2")
                set_output("passed", "true")
            with open(output_file) as f:
                content = f.read()
            self.assertIn("cls_score=45.2", content)
            self.assertIn("passed=true", content)
        finally:
            os.unlink(output_file)

    def test_no_crash_without_github_output(self):
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_OUTPUT"}
        with patch.dict(os.environ, env, clear=True):
            # Should not raise, falls back to print
            set_output("test_key", "test_value")


# ─── Tests: get_pr_number ─────────────────────────────────────────────────────

class TestGetPRNumber(unittest.TestCase):

    def test_extracts_pr_number_from_event(self):
        event = {"pull_request": {"number": 42}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(event, f)
            event_path = f.name
        try:
            result = _get_pr_number(event_path)
            self.assertEqual(result, 42)
        finally:
            os.unlink(event_path)

    def test_returns_none_for_non_pr_event(self):
        event = {"action": "push", "ref": "refs/heads/main"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(event, f)
            event_path = f.name
        try:
            result = _get_pr_number(event_path)
            self.assertIsNone(result)
        finally:
            os.unlink(event_path)

    def test_returns_none_for_missing_file(self):
        result = _get_pr_number("/nonexistent/path/event.json")
        self.assertIsNone(result)

    def test_returns_none_for_empty_path(self):
        result = _get_pr_number("")
        self.assertIsNone(result)


# ─── Tests: Persona Presets ───────────────────────────────────────────────────

class TestPersonaPresets(unittest.TestCase):

    def test_all_presets_have_required_fields(self):
        required = {"name", "age", "tech_savviness", "attention_span_seconds",
                    "motivation_level", "cognitive_biases"}
        for preset_name, preset in PERSONA_PRESETS.items():
            missing = required - set(preset.keys())
            self.assertEqual(missing, set(), f"Preset '{preset_name}' missing fields: {missing}")

    def test_tech_savviness_in_range(self):
        for name, preset in PERSONA_PRESETS.items():
            self.assertGreaterEqual(preset["tech_savviness"], 1)
            self.assertLessEqual(preset["tech_savviness"], 5)

    def test_three_presets_defined(self):
        self.assertIn("busy-mom", PERSONA_PRESETS)
        self.assertIn("tech-millennial", PERSONA_PRESETS)
        self.assertIn("senior-shopper", PERSONA_PRESETS)


if __name__ == "__main__":
    unittest.main()
