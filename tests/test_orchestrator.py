"""
Unit Tests for the Orchestrator Module.

Tests cover:
- ScenarioLoader: validation, loading, error handling
- Orchestrator: full loop execution, dropout logic, output format
- CLI integration: end-to-end scenario run
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.orchestrator.loader import ScenarioLoader, ScenarioValidationError
from src.orchestrator.orchestrator import Orchestrator


# ─── Fixtures ──────────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def loader():
    """Create a ScenarioLoader instance."""
    return ScenarioLoader()


@pytest.fixture
def valid_scenario_path():
    """Path to a valid scenario fixture."""
    return str(FIXTURES_DIR / "sample_scenario.json")


@pytest.fixture
def invalid_scenario_path():
    """Path to an invalid scenario fixture."""
    return str(FIXTURES_DIR / "invalid_scenario.json")


@pytest.fixture
def mock_persona_engine():
    """Mock PersonaEngine that returns predictable outputs."""
    engine = MagicMock()
    engine.get_system_prompt.return_value = "You are a test persona."
    engine.get_cognitive_constraints.return_value = {
        "max_steps": 3,
        "complexity_tolerance": 2,
        "dropout_threshold": 70,
    }
    return engine


@pytest.fixture
def mock_navigation_engine():
    """Mock NavigationEngine that returns predictable DOM states."""
    engine = MagicMock()

    mock_elements = [
        {"tag": "h1", "text": "Test Page", "selector": "h1", "aria_label": ""},
        {"tag": "button", "text": "Continue", "selector": "button.cta", "aria_label": "Continue"},
        {"tag": "input", "text": "", "selector": "input[name='email']", "aria_label": "Email", "value": ""},
    ]

    nav_state = {
        "current_url": "https://test.example.com",
        "page_title": "Test Page",
        "dom_tree_json": json.dumps({"elements": mock_elements, "page_title": "Test Page"}),
        "screenshot_path": "screenshots/test.png",
        "elements": mock_elements,
        "last_action": "navigate",
    }

    engine.navigate_to.return_value = nav_state
    engine.perform_action.return_value = {
        "current_url": "https://test.example.com/step2",
        "page_title": "Step 2",
        "dom_tree_json": json.dumps({"elements": [], "page_title": "Step 2"}),
        "screenshot_path": "screenshots/test_step2.png",
        "elements": [],
        "last_action": "click:button.cta",
    }
    engine.close.return_value = None
    return engine


@pytest.fixture
def mock_evaluation_engine_normal():
    """Mock EvaluationEngine that returns moderate CLS scores (no dropout)."""
    engine = MagicMock()
    engine.evaluate_step.return_value = {
        "visual_complexity_score": 40,
        "interaction_friction_score": 35,
        "cognitive_alignment_score": 60,
        "composite_cls": 38,
        "identified_friction_points": [
            {
                "severity": "low",
                "description": "Minor layout issue detected.",
                "recommendation": "Consider simplifying the page structure.",
            }
        ],
    }
    return engine


@pytest.fixture
def mock_evaluation_engine_high_cls():
    """Mock EvaluationEngine that returns high CLS scores (triggers dropout)."""
    engine = MagicMock()
    engine.evaluate_step.return_value = {
        "visual_complexity_score": 90,
        "interaction_friction_score": 85,
        "cognitive_alignment_score": 20,
        "composite_cls": 85,
        "identified_friction_points": [
            {
                "severity": "critical",
                "description": "Page is extremely complex for this persona.",
                "recommendation": "Redesign the page with progressive disclosure.",
            }
        ],
    }
    return engine


@pytest.fixture
def mock_reporting_engine():
    """Mock ReportingEngine."""
    engine = MagicMock()
    engine.generate_html_report.return_value = "/tmp/test_report.html"
    return engine


# ─── ScenarioLoader Tests ──────────────────────────────────────────────────────


class TestScenarioLoader:
    """Tests for the ScenarioLoader class."""

    def test_load_valid_scenario(self, loader, valid_scenario_path):
        """Test that a valid scenario loads successfully."""
        scenario = loader.load(valid_scenario_path)
        assert scenario["scenario_id"] == "checkout-flow-busy-mom"
        assert scenario["target_url"] == "https://shopee.tw/checkout"
        assert scenario["persona"]["name"] == "Busy Mom (Amy)"
        assert scenario["persona"]["tech_savviness"] == 2
        assert scenario["max_steps"] == 5

    def test_load_invalid_scenario_raises_validation_error(self, loader, invalid_scenario_path):
        """Test that an invalid scenario raises ScenarioValidationError."""
        with pytest.raises(ScenarioValidationError):
            loader.load(invalid_scenario_path)

    def test_load_nonexistent_file_raises_file_not_found(self, loader):
        """Test that loading a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            loader.load("/nonexistent/path/scenario.json")

    def test_load_from_dict_valid(self, loader):
        """Test that load_from_dict validates a correct dictionary."""
        data = {
            "scenario_id": "test-1",
            "target_url": "https://example.com",
            "target_goal": "Test goal",
            "persona": {
                "name": "Test User",
                "tech_savviness": 3,
                "attention_span_seconds": 60,
                "motivation_level": 4,
            },
        }
        result = loader.load_from_dict(data)
        assert result["scenario_id"] == "test-1"

    def test_load_from_dict_invalid(self, loader):
        """Test that load_from_dict raises error for invalid data."""
        data = {"scenario_id": "test-1"}  # Missing required fields
        with pytest.raises(ScenarioValidationError):
            loader.load_from_dict(data)


# ─── Orchestrator Tests ────────────────────────────────────────────────────────


class TestOrchestrator:
    """Tests for the Orchestrator class."""

    def test_run_scenario_returns_correct_keys(
        self, mock_persona_engine, mock_navigation_engine, mock_evaluation_engine_normal, valid_scenario_path
    ):
        """Test that run_scenario returns a dict with all expected keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = Orchestrator(
                persona_engine=mock_persona_engine,
                navigation_engine=mock_navigation_engine,
                evaluation_engine=mock_evaluation_engine_normal,
                output_dir=tmpdir,
            )
            result = orchestrator.run_scenario(valid_scenario_path)

            required_keys = [
                "scenario_id", "target_url", "target_goal", "persona_name",
                "steps", "final_cls", "total_steps", "dropout",
                "dropout_reason", "execution_time_seconds", "timestamp",
            ]
            for key in required_keys:
                assert key in result, f"Missing key: {key}"

    def test_run_scenario_correct_scenario_id(
        self, mock_persona_engine, mock_navigation_engine, mock_evaluation_engine_normal, valid_scenario_path
    ):
        """Test that the scenario_id matches the input fixture."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = Orchestrator(
                persona_engine=mock_persona_engine,
                navigation_engine=mock_navigation_engine,
                evaluation_engine=mock_evaluation_engine_normal,
                output_dir=tmpdir,
            )
            result = orchestrator.run_scenario(valid_scenario_path)
            assert result["scenario_id"] == "checkout-flow-busy-mom"

    def test_run_scenario_no_dropout_with_low_cls(
        self, mock_persona_engine, mock_navigation_engine, mock_evaluation_engine_normal, valid_scenario_path
    ):
        """Test that the persona does not drop out when CLS is below threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = Orchestrator(
                persona_engine=mock_persona_engine,
                navigation_engine=mock_navigation_engine,
                evaluation_engine=mock_evaluation_engine_normal,
                output_dir=tmpdir,
            )
            result = orchestrator.run_scenario(valid_scenario_path)
            assert result["dropout"] is False
            assert result["dropout_reason"] == ""

    def test_run_scenario_dropout_with_high_cls(
        self, mock_persona_engine, mock_navigation_engine, mock_evaluation_engine_high_cls, valid_scenario_path
    ):
        """Test that the persona drops out when CLS exceeds the threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = Orchestrator(
                persona_engine=mock_persona_engine,
                navigation_engine=mock_navigation_engine,
                evaluation_engine=mock_evaluation_engine_high_cls,
                output_dir=tmpdir,
            )
            result = orchestrator.run_scenario(valid_scenario_path)
            assert result["dropout"] is True
            assert "exceeded dropout threshold" in result["dropout_reason"]
            assert result["total_steps"] == 1  # Stops at first step

    def test_run_scenario_saves_trace_file(
        self, mock_persona_engine, mock_navigation_engine, mock_evaluation_engine_normal, valid_scenario_path
    ):
        """Test that the execution trace is saved as a JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = Orchestrator(
                persona_engine=mock_persona_engine,
                navigation_engine=mock_navigation_engine,
                evaluation_engine=mock_evaluation_engine_normal,
                output_dir=tmpdir,
            )
            result = orchestrator.run_scenario(valid_scenario_path)

            trace_path = Path(tmpdir) / f"{result['scenario_id']}_trace.json"
            assert trace_path.exists()

            with open(trace_path) as f:
                trace_data = json.load(f)
            assert trace_data["scenario_id"] == result["scenario_id"]
            assert len(trace_data["steps"]) == result["total_steps"]

    def test_run_scenario_with_reporting_engine(
        self, mock_persona_engine, mock_navigation_engine, mock_evaluation_engine_normal,
        mock_reporting_engine, valid_scenario_path
    ):
        """Test that the reporting engine is called when provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = Orchestrator(
                persona_engine=mock_persona_engine,
                navigation_engine=mock_navigation_engine,
                evaluation_engine=mock_evaluation_engine_normal,
                reporting_engine=mock_reporting_engine,
                output_dir=tmpdir,
            )
            result = orchestrator.run_scenario(valid_scenario_path)
            mock_reporting_engine.generate_html_report.assert_called_once()

    def test_final_cls_is_average_of_steps(
        self, mock_persona_engine, mock_navigation_engine, mock_evaluation_engine_normal, valid_scenario_path
    ):
        """Test that final_cls is the average of all step composite_cls values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = Orchestrator(
                persona_engine=mock_persona_engine,
                navigation_engine=mock_navigation_engine,
                evaluation_engine=mock_evaluation_engine_normal,
                output_dir=tmpdir,
            )
            result = orchestrator.run_scenario(valid_scenario_path)

            step_scores = [s["composite_cls"] for s in result["steps"] if s["composite_cls"] > 0]
            expected_avg = round(sum(step_scores) / len(step_scores), 2) if step_scores else 0.0
            assert result["final_cls"] == expected_avg

    def test_steps_contain_friction_points(
        self, mock_persona_engine, mock_navigation_engine, mock_evaluation_engine_normal, valid_scenario_path
    ):
        """Test that steps contain identified friction points."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = Orchestrator(
                persona_engine=mock_persona_engine,
                navigation_engine=mock_navigation_engine,
                evaluation_engine=mock_evaluation_engine_normal,
                output_dir=tmpdir,
            )
            result = orchestrator.run_scenario(valid_scenario_path)

            # At least one step should have friction points (from mock)
            all_fps = []
            for step in result["steps"]:
                all_fps.extend(step.get("identified_friction_points", []))
            assert len(all_fps) > 0
            assert "severity" in all_fps[0]
            assert "description" in all_fps[0]
            assert "recommendation" in all_fps[0]
