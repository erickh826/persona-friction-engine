import json
from pathlib import Path

import jsonschema
import pytest

from src.evaluation.engine import CognitiveEvaluationEngine
from src.evaluation.models import StepEvaluationResult

SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "step_evaluation.json"


def _element(tag: str = "div", text: str = "", aria_label: str = "") -> dict:
    return {
        "tag": tag,
        "text": text,
        "aria_label": aria_label,
        "href": "",
        "bounding_box": {"x": 0, "y": 0, "width": 10, "height": 10},
    }


@pytest.fixture
def engine() -> CognitiveEvaluationEngine:
    return CognitiveEvaluationEngine(use_llm=False)


@pytest.fixture
def persona_constraints() -> dict:
    return {
        "max_steps": 3,
        "complexity_tolerance": 2,
        "dropout_threshold": 70,
    }


class FakeVisionClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict] = []

    def analyze_step(self, *, screenshot_path, dom_state, persona_constraints):
        self.calls.append(
            {
                "screenshot_path": screenshot_path,
                "dom_state": dom_state,
                "persona_constraints": persona_constraints,
            }
        )
        return self.payload


def test_visual_complexity_high_element_count(engine, persona_constraints):
    dom_state = {"elements": [_element() for _ in range(60)]}
    result = engine.evaluate_step(dom_state, persona_constraints)

    assert result.visual_complexity_score >= 80


def test_no_cta_produces_high_severity_friction_point(engine, persona_constraints):
    dom_state = {
        "elements": [
            _element("p", "Some paragraph without a call to action."),
            _element("div", "Another block of text."),
        ]
    }
    result = engine.evaluate_step(dom_state, persona_constraints)

    assert any(
        fp.severity == "high" and "call-to-action" in fp.description.lower()
        for fp in result.identified_friction_points
    )


def test_composite_cls_is_deterministic(engine, persona_constraints):
    dom_state = {
        "elements": [
            _element("button", "Buy Now", "Buy now"),
            _element("input", "", ""),
        ]
    }

    first = engine.evaluate_step(dom_state, persona_constraints)
    second = engine.evaluate_step(dom_state, persona_constraints)

    assert first == second
    assert first.composite_cls == second.composite_cls


def test_step_evaluation_result_validates_against_schema(engine, persona_constraints):
    dom_state = {"elements": [_element("button", "Buy Now", "Buy now")]}
    result = engine.evaluate_step(dom_state, persona_constraints)

    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    payload = result.model_dump()
    payload.update(
        {
            "step_number": 1,
            "current_url": "https://example.com",
            "action_taken": "navigate",
        }
    )
    jsonschema.validate(instance=payload, schema=schema)


def test_llm_evaluation_uses_client_and_recalculates_cls(persona_constraints):
    llm_payload = {
        "visual_complexity_score": 80,
        "interaction_friction_score": 60,
        "cognitive_alignment_score": 40,
        "composite_cls": 1,
        "identified_friction_points": [
            {
                "severity": "high",
                "description": "Poor contrast around the primary CTA near the top right.",
                "recommendation": "Increase CTA contrast and surrounding whitespace.",
            }
        ],
    }
    fake_client = FakeVisionClient(llm_payload)
    engine = CognitiveEvaluationEngine(use_llm=True, llm_client=fake_client)
    dom_state = {"elements": [_element("button", "Sign Up", "Sign up")]}

    result = engine.evaluate_step(
        dom_state,
        persona_constraints,
        screenshot_path="screenshots/step-1.png",
    )

    assert fake_client.calls == [
        {
            "screenshot_path": "screenshots/step-1.png",
            "dom_state": dom_state,
            "persona_constraints": persona_constraints,
        }
    ]
    assert result.composite_cls == 67
    assert result.identified_friction_points[0].severity == "high"


def test_llm_evaluation_result_validates_against_schema(persona_constraints):
    fake_client = FakeVisionClient(
        {
            "visual_complexity_score": 45,
            "interaction_friction_score": 55,
            "cognitive_alignment_score": 75,
            "identified_friction_points": [
                {
                    "severity": "medium",
                    "description": "The CTA is visually present but competes with nearby links.",
                    "recommendation": "Reduce competing link emphasis near the CTA.",
                }
            ],
        }
    )
    engine = CognitiveEvaluationEngine(use_llm=True, llm_client=fake_client)
    result = engine.evaluate_step(
        {"elements": [_element("a", "Get Started", "Get started")]},
        persona_constraints,
        screenshot_path="screenshots/step-2.png",
    )

    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    payload = result.model_dump()
    payload.update(
        {
            "step_number": 1,
            "current_url": "https://example.com",
            "action_taken": "click",
            "screenshot_path": "screenshots/step-2.png",
        }
    )
    jsonschema.validate(instance=payload, schema=schema)


def test_use_llm_requires_api_key_when_no_client(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        CognitiveEvaluationEngine(use_llm=True)
