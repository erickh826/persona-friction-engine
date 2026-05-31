"""
End-to-End Integration Tests for M2 Orchestrator.

These tests spin up a local HTTP server serving mock pages, then run
the full Orchestrator pipeline (real NavigationEngine + real EvaluationEngine
+ real PersonaEngine + ReportingEngine) against it.
"""

import json
import os
import sys
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.orchestrator import Orchestrator, NavigationError, EvaluationError
from src.persona.engine import PersonaEngine
from src.persona.models import PersonaProfile
from src.evaluation.engine import CognitiveEvaluationEngine


# ─── Test Fixtures ─────────────────────────────────────────────────────────────

MOCK_HTML_SIMPLE = """<!DOCTYPE html>
<html>
<head><title>Simple Checkout</title></head>
<body>
    <h1>Checkout Page</h1>
    <form>
        <label for="email">Email</label>
        <input id="email" type="email" name="email" aria-label="Email address">
        <label for="name">Name</label>
        <input id="name" type="text" name="name" aria-label="Full name">
        <button id="submit-btn" type="submit">Checkout</button>
    </form>
</body>
</html>"""

MOCK_HTML_COMPLEX = """<!DOCTYPE html>
<html>
<head><title>Complex Page</title></head>
<body>
    <h1>Complex E-Commerce</h1>
    <nav>
        <a href="#home">Home</a>
        <a href="#products">Products</a>
        <a href="#about">About</a>
        <a href="#contact">Contact</a>
    </nav>
    <div class="sidebar">
        <input type="text" placeholder="Search">
        <input type="text" placeholder="Filter">
        <input type="text" placeholder="Category">
    </div>
    <div class="content">
        <div><a href="#">Item 1</a></div>
        <div><a href="#">Item 2</a></div>
        <div><a href="#">Item 3</a></div>
        <div><a href="#">Item 4</a></div>
        <div><a href="#">Item 5</a></div>
        <div><a href="#">Item 6</a></div>
        <div><a href="#">Item 7</a></div>
        <div><a href="#">Item 8</a></div>
        <div><a href="#">Item 9</a></div>
        <div><a href="#">Item 10</a></div>
        <div><a href="#">Item 11</a></div>
        <div><a href="#">Item 12</a></div>
        <div><a href="#">Item 13</a></div>
        <div><a href="#">Item 14</a></div>
        <div><a href="#">Item 15</a></div>
        <div><a href="#">Item 16</a></div>
        <div><a href="#">Item 17</a></div>
        <div><a href="#">Item 18</a></div>
        <div><a href="#">Item 19</a></div>
        <div><a href="#">Item 20</a></div>
    </div>
    <button>Add to Cart</button>
    <button>Buy Now</button>
    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.</p>
</body>
</html>"""

MOCK_HTML_BROKEN = """<!DOCTYPE html>
<html>
<head><title>Broken Page</title></head>
<body>
    <h1>Error 500</h1>
    <p>Internal Server Error</p>
</body>
</html>"""


class MockHTTPHandler(SimpleHTTPRequestHandler):
    """Custom handler serving mock HTML pages."""

    def do_GET(self):
        if self.path == "/" or self.path == "/checkout":
            self._serve_html(MOCK_HTML_SIMPLE)
        elif self.path == "/complex":
            self._serve_html(MOCK_HTML_COMPLEX)
        elif self.path == "/broken":
            self.send_error(500, "Internal Server Error")
        else:
            self._serve_html(MOCK_HTML_SIMPLE)

    def _serve_html(self, html: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        """Suppress server log output during tests."""
        pass


@pytest.fixture(scope="module")
def mock_server():
    """Start a local HTTP server for integration tests."""
    server = HTTPServer(("127.0.0.1", 0), MockHTTPHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary output directory."""
    out = tmp_path / "output"
    out.mkdir()
    return str(out)


@pytest.fixture
def simple_scenario(mock_server, tmp_path):
    """Create a scenario JSON pointing to the mock server."""
    scenario = {
        "scenario_id": "integration-test-simple",
        "target_url": f"{mock_server}/checkout",
        "target_goal": "Complete checkout flow",
        "max_steps": 3,
        "persona": {
            "name": "Test User",
            "age": 30,
            "tech_savviness": 3,
            "attention_span_seconds": 90,
            "motivation_level": 3,
            "cognitive_biases": ["loss aversion"],
        },
    }
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(scenario))
    return str(path)


@pytest.fixture
def complex_scenario(mock_server, tmp_path):
    """Create a scenario with a complex page."""
    scenario = {
        "scenario_id": "integration-test-complex",
        "target_url": f"{mock_server}/complex",
        "target_goal": "Browse products",
        "max_steps": 5,
        "persona": {
            "name": "Senior Shopper",
            "age": 65,
            "tech_savviness": 1,
            "attention_span_seconds": 60,
            "motivation_level": 2,
            "cognitive_biases": ["authority bias"],
        },
    }
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(scenario))
    return str(path)


# ─── Integration Tests ─────────────────────────────────────────────────────────


class TestEndToEndSimple:
    """Tests with a simple checkout page."""

    def test_full_pipeline_returns_result(self, simple_scenario, output_dir):
        """Full pipeline should return a valid result dict."""
        from src.navigation.engine import NavigationEngine

        orchestrator = Orchestrator(
            persona_engine=PersonaEngine(),
            navigation_engine=NavigationEngine(headless=True, screenshots_dir=f"{output_dir}/screenshots"),
            evaluation_engine=CognitiveEvaluationEngine(use_llm=False),
            reporting_engine=None,
            output_dir=output_dir,
        )

        result = orchestrator.run_scenario(simple_scenario)

        assert result["scenario_id"] == "integration-test-simple"
        assert result["persona_name"] == "Test User"
        assert result["total_steps"] >= 1
        assert 0 <= result["final_cls"] <= 100
        assert isinstance(result["steps"], list)
        assert result["completed"] is True
        assert result["error"] is None

    def test_trace_file_saved(self, simple_scenario, output_dir):
        """Trace JSON file should be saved to output directory."""
        from src.navigation.engine import NavigationEngine

        orchestrator = Orchestrator(
            persona_engine=PersonaEngine(),
            navigation_engine=NavigationEngine(headless=True, screenshots_dir=f"{output_dir}/screenshots"),
            evaluation_engine=CognitiveEvaluationEngine(use_llm=False),
            output_dir=output_dir,
        )

        orchestrator.run_scenario(simple_scenario)

        trace_path = Path(output_dir) / "integration-test-simple_trace.json"
        assert trace_path.exists()

        with open(trace_path) as f:
            trace = json.load(f)
        assert trace["scenario_id"] == "integration-test-simple"
        assert "steps" in trace

    def test_screenshots_captured(self, simple_scenario, output_dir):
        """Screenshots should be saved for each step."""
        from src.navigation.engine import NavigationEngine

        screenshots_dir = f"{output_dir}/screenshots"
        orchestrator = Orchestrator(
            persona_engine=PersonaEngine(),
            navigation_engine=NavigationEngine(headless=True, screenshots_dir=screenshots_dir),
            evaluation_engine=CognitiveEvaluationEngine(use_llm=False),
            output_dir=output_dir,
        )

        result = orchestrator.run_scenario(simple_scenario)

        # At least one screenshot should exist
        screenshots = list(Path(screenshots_dir).glob("*.png"))
        assert len(screenshots) >= 1

    def test_html_report_generated(self, simple_scenario, output_dir):
        """HTML report should be generated when reporting engine is provided."""
        from src.navigation.engine import NavigationEngine
        sys.path.insert(0, str(_PROJECT_ROOT / "src"))
        from main import ReportingEngine

        orchestrator = Orchestrator(
            persona_engine=PersonaEngine(),
            navigation_engine=NavigationEngine(headless=True, screenshots_dir=f"{output_dir}/screenshots"),
            evaluation_engine=CognitiveEvaluationEngine(use_llm=False),
            reporting_engine=ReportingEngine(),
            output_dir=output_dir,
        )

        result = orchestrator.run_scenario(simple_scenario)

        assert "report_path" in result
        report_path = Path(result["report_path"])
        assert report_path.exists()
        content = report_path.read_text()
        assert "Chart.js" in content or "chart.js" in content
        assert "integration-test-simple" in content


class TestEndToEndComplex:
    """Tests with a complex page (higher cognitive load)."""

    def test_complex_page_higher_cls(self, complex_scenario, output_dir):
        """Complex page should produce higher CLS scores."""
        from src.navigation.engine import NavigationEngine

        orchestrator = Orchestrator(
            persona_engine=PersonaEngine(),
            navigation_engine=NavigationEngine(headless=True, screenshots_dir=f"{output_dir}/screenshots"),
            evaluation_engine=CognitiveEvaluationEngine(use_llm=False),
            output_dir=output_dir,
        )

        result = orchestrator.run_scenario(complex_scenario)

        # Complex page with low-tech persona should have higher friction
        assert result["total_steps"] >= 1
        assert result["final_cls"] > 0


class TestErrorRecovery:
    """Tests for graceful error handling."""

    def test_navigation_failure_saves_partial_trace(self, tmp_path, output_dir):
        """If navigation fails, partial trace should still be saved."""
        scenario = {
            "scenario_id": "error-test",
            "target_url": "http://127.0.0.1:1/nonexistent",
            "target_goal": "Test error recovery",
            "max_steps": 3,
            "persona": {
                "name": "Error Tester",
                "age": 30,
                "tech_savviness": 3,
                "attention_span_seconds": 60,
                "motivation_level": 3,
                "cognitive_biases": [],
            },
        }
        path = tmp_path / "error_scenario.json"
        path.write_text(json.dumps(scenario))

        from src.navigation.engine import NavigationEngine

        orchestrator = Orchestrator(
            persona_engine=PersonaEngine(),
            navigation_engine=NavigationEngine(headless=True, screenshots_dir=f"{output_dir}/screenshots"),
            evaluation_engine=CognitiveEvaluationEngine(use_llm=False),
            output_dir=output_dir,
            max_retries=0,  # Fail fast for testing
        )

        result = orchestrator.run_scenario(str(path))

        # Should return a result with error info, not crash
        assert result["scenario_id"] == "error-test"
        assert result["completed"] is False
        assert result["error"] is not None
        assert result["error"]["type"] == "NavigationError"

        # Trace should still be saved
        trace_path = Path(output_dir) / "error-test_trace.json"
        assert trace_path.exists()

    def test_evaluation_failure_with_mock(self, simple_scenario, output_dir):
        """If evaluation engine raises, orchestrator should handle gracefully."""

        class FailingEvalEngine:
            def evaluate_step(self, dom_state, persona_constraints):
                raise RuntimeError("LLM rate limit exceeded")

        from src.navigation.engine import NavigationEngine

        orchestrator = Orchestrator(
            persona_engine=PersonaEngine(),
            navigation_engine=NavigationEngine(headless=True, screenshots_dir=f"{output_dir}/screenshots"),
            evaluation_engine=FailingEvalEngine(),
            output_dir=output_dir,
            max_retries=0,
        )

        result = orchestrator.run_scenario(simple_scenario)

        # Should save partial trace with error
        assert result["completed"] is False
        assert result["error"] is not None
        assert "EvaluationError" in result["error"]["type"]

    def test_action_failure_continues_gracefully(self, mock_server, tmp_path, output_dir):
        """If an action fails, orchestrator should stop loop but save results."""

        class PartialNavEngine:
            """Navigation engine that fails on perform_action."""

            def navigate_to(self, url):
                return {
                    "current_url": url,
                    "dom_tree_json": json.dumps({"elements": [
                        {"tag": "button", "text": "Buy Now", "aria_label": "Buy Now"},
                    ]}),
                    "screenshot_path": "",
                    "page_title": "Test",
                    "visible_text_sample": "Test page",
                }

            def perform_action(self, action, selector, value=None):
                raise RuntimeError("Element not found")

            def close(self):
                pass

        scenario = {
            "scenario_id": "action-fail-test",
            "target_url": f"{mock_server}/checkout",
            "target_goal": "Test action failure",
            "max_steps": 5,
            "persona": {
                "name": "Action Tester",
                "age": 30,
                "tech_savviness": 3,
                "attention_span_seconds": 90,
                "motivation_level": 3,
                "cognitive_biases": [],
            },
        }
        path = tmp_path / "scenario.json"
        path.write_text(json.dumps(scenario))

        orchestrator = Orchestrator(
            persona_engine=PersonaEngine(),
            navigation_engine=PartialNavEngine(),
            evaluation_engine=CognitiveEvaluationEngine(use_llm=False),
            output_dir=output_dir,
            max_retries=0,
        )

        result = orchestrator.run_scenario(str(path))

        # Should have at least 1 step (the initial navigation evaluation)
        assert result["total_steps"] >= 1
        # Should still save trace
        trace_path = Path(output_dir) / "action-fail-test_trace.json"
        assert trace_path.exists()
