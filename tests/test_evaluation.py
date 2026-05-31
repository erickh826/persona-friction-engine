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


def test_use_llm_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        CognitiveEvaluationEngine(use_llm=True)
