from pathlib import Path

from src.reporting.engine import ReportingEngine


def _sample_run_result() -> dict:
    return {
        "scenario_id": "checkout-audit",
        "target_url": "https://example.com/checkout",
        "target_goal": "Complete checkout <fast>",
        "persona_name": "Senior Shopper",
        "final_cls": 67.5,
        "total_steps": 2,
        "dropout": True,
        "dropout_reason": "Composite CLS exceeded threshold.",
        "execution_time_seconds": 1.23,
        "steps": [
            {
                "step_number": 1,
                "current_url": "https://example.com/cart",
                "action_taken": "navigate",
                "visual_complexity_score": 42,
                "interaction_friction_score": 50,
                "cognitive_alignment_score": 72,
                "composite_cls": 42,
                "screenshot_path": "screenshots/step_001.png",
                "identified_friction_points": [
                    {
                        "severity": "high",
                        "description": "CTA is visually hidden near the fold.",
                        "recommendation": "Move the primary CTA above the fold.",
                        "coordinates": {
                            "x": 180,
                            "y": 120,
                            "width": 240,
                            "height": 80,
                            "image_width": 1200,
                            "image_height": 800,
                        },
                    }
                ],
            },
            {
                "step_number": 2,
                "current_url": "https://example.com/checkout",
                "action_taken": "click:#checkout",
                "visual_complexity_score": 84,
                "interaction_friction_score": 73,
                "cognitive_alignment_score": 38,
                "composite_cls": 74,
                "screenshot_path": "screenshots/step_002.png",
                "identified_friction_points": [
                    {
                        "severity": "critical",
                        "description": "Payment error copy is unclear.",
                        "recommendation": "Explain how to recover from the payment error.",
                    }
                ],
            },
        ],
    }


def test_generate_html_report_writes_interactive_dashboard(tmp_path):
    output_path = tmp_path / "reports" / "checkout_report.html"

    result_path = ReportingEngine().generate_html_report(
        _sample_run_result(), str(output_path)
    )

    html = output_path.read_text(encoding="utf-8")
    assert result_path == str(output_path)
    assert output_path.is_file()
    assert "https://cdn.tailwindcss.com" in html
    assert "https://cdn.jsdelivr.net/npm/chart.js" in html
    assert "Step Timeline" in html
    assert "Friction Points Inspector" in html
    assert '"clsScores":[42,74]' in html
    assert '"dropoutStep":"Step 2"' in html


def test_report_escapes_html_content_and_does_not_fetch_external_assets(tmp_path, monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("template rendering should not perform network calls")

    monkeypatch.setattr("urllib.request.urlopen", fail_network)
    output_path = tmp_path / "safe_report.html"

    ReportingEngine().generate_html_report(_sample_run_result(), str(output_path))

    html = output_path.read_text(encoding="utf-8")
    assert "Complete checkout &lt;fast&gt;" in html
    assert "Complete checkout <fast>" not in html


def test_report_color_codes_severity_and_renders_coordinate_overlay(tmp_path):
    output_path = tmp_path / "overlay_report.html"

    ReportingEngine().generate_html_report(_sample_run_result(), str(output_path))

    html = output_path.read_text(encoding="utf-8")
    assert "bg-orange-100 text-orange-800" in html
    assert "bg-red-100 text-red-800" in html
    assert "style=\"left:15%; top:15%; width:20%; height:10%;\"" in html
    assert "Overlay: x=15%, y=15%, width=20%, height=10%" in html


def test_report_rewrites_local_screenshot_paths_relative_to_report(tmp_path):
    screenshot_dir = tmp_path / "screenshots"
    screenshot_dir.mkdir()
    screenshot_path = screenshot_dir / "step_001.svg"
    screenshot_path.write_text("<svg></svg>", encoding="utf-8")
    output_path = tmp_path / "reports" / "report.html"
    run_result = _sample_run_result()
    run_result["steps"][0]["screenshot_path"] = str(screenshot_path)

    ReportingEngine().generate_html_report(run_result, str(output_path))

    html = output_path.read_text(encoding="utf-8")
    assert 'src="../screenshots/step_001.svg"' in html


def test_report_handles_empty_steps(tmp_path):
    output_path = tmp_path / "empty_report.html"
    run_result = _sample_run_result()
    run_result["steps"] = []
    run_result["total_steps"] = 0
    run_result["dropout"] = False

    ReportingEngine().generate_html_report(run_result, str(output_path))

    html = output_path.read_text(encoding="utf-8")
    assert "No steps recorded." in html
    assert '"clsScores":[]' in html
