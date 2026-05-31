import json
from unittest.mock import MagicMock, patch

import pytest

from src.persona.engine import PersonaEngine, _BIAS_BEHAVIORAL_HINTS
from src.persona.fixtures import (
    PERSONA_BUSY_MOM,
    PERSONA_SENIOR_SHOPPER,
    PERSONA_TECH_MILLENNIAL,
)
from src.persona.models import PersonaProfile, PersonaState


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_state(**kwargs) -> PersonaState:
    return PersonaState(**kwargs)


def _make_mock_llm_response(action: str, selector: str = "", value: str = "", thought: str = "test") -> MagicMock:
    """Return a mock openai-style response object."""
    payload = json.dumps({
        "action": action,
        "selector": selector,
        "value": value,
        "thought_process": thought,
    })
    choice = MagicMock()
    choice.message.content = payload
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_mock_client(action: str = "click", selector: str = "button.cta",
                      value: str = "", thought: str = "This button looks clickable.") -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value = _make_mock_llm_response(
        action, selector, value, thought
    )
    return client


DOM_STATE = {
    "current_url": "https://example.com/checkout",
    "elements": [
        {"tag": "button", "text": "Continue", "selector": "button.cta", "aria_label": "Continue"},
        {"tag": "input", "text": "", "selector": "input[name='email']", "aria_label": "Email"},
    ],
}


# ---------------------------------------------------------------------------
# PersonaState model tests
# ---------------------------------------------------------------------------

class TestPersonaState:
    def test_default_state_has_full_patience_and_motivation(self):
        state = PersonaState()
        assert state.remaining_patience == 1.0
        assert state.current_motivation == 1.0
        assert state.confusion_level == 0.0
        assert state.execution_history == []

    def test_custom_values_are_stored(self):
        state = PersonaState(remaining_patience=0.5, current_motivation=0.7, confusion_level=0.3)
        assert state.remaining_patience == 0.5
        assert state.current_motivation == 0.7
        assert state.confusion_level == 0.3

    def test_patience_clamped_to_range(self):
        with pytest.raises(Exception):
            PersonaState(remaining_patience=1.1)
        with pytest.raises(Exception):
            PersonaState(remaining_patience=-0.1)

    def test_confusion_clamped_to_range(self):
        with pytest.raises(Exception):
            PersonaState(confusion_level=1.1)

    def test_execution_history_stores_entries(self):
        entry = {"action": "click", "selector": "button.cta", "value": "", "thought_process": "Looks right"}
        state = PersonaState(execution_history=[entry])
        assert len(state.execution_history) == 1
        assert state.execution_history[0]["action"] == "click"

    def test_extra_fields_are_forbidden(self):
        with pytest.raises(Exception):
            PersonaState(unknown_field="x")


# ---------------------------------------------------------------------------
# Existing M1 tests (preserved)
# ---------------------------------------------------------------------------

class TestPersonaEngine:
    def setup_method(self):
        self.engine = PersonaEngine()
        self.fixtures = [
            PERSONA_BUSY_MOM,
            PERSONA_TECH_MILLENNIAL,
            PERSONA_SENIOR_SHOPPER,
        ]

    def test_get_system_prompt_returns_non_empty_string_for_each_fixture(self):
        for profile in self.fixtures:
            prompt = self.engine.get_system_prompt(profile)

            assert isinstance(prompt, str)
            assert prompt.strip()
            assert profile.name in prompt

    def test_get_cognitive_constraints_returns_expected_keys(self):
        constraints = self.engine.get_cognitive_constraints(PERSONA_BUSY_MOM)

        assert set(constraints.keys()) == {
            "max_steps",
            "complexity_tolerance",
            "dropout_threshold",
        }

    def test_max_steps_is_always_at_least_one(self):
        for profile in self.fixtures:
            constraints = self.engine.get_cognitive_constraints(profile)
            assert constraints["max_steps"] >= 1


# ---------------------------------------------------------------------------
# decide_next_action tests
# ---------------------------------------------------------------------------

class TestDecideNextAction:
    def setup_method(self):
        self.state = PersonaState()

    def test_returns_required_keys(self):
        client = _make_mock_client("click", "button.cta", "", "Looks promising.")
        engine = PersonaEngine(llm_client=client)
        result = engine.decide_next_action(PERSONA_BUSY_MOM, self.state, DOM_STATE)
        assert set(result.keys()) == {"action", "selector", "value", "thought_process"}

    def test_valid_action_click_is_parsed(self):
        client = _make_mock_client("click", "button.cta")
        engine = PersonaEngine(llm_client=client)
        result = engine.decide_next_action(PERSONA_BUSY_MOM, self.state, DOM_STATE)
        assert result["action"] == "click"
        assert result["selector"] == "button.cta"

    def test_valid_action_fill_is_parsed(self):
        client = _make_mock_client("fill", "input[name='email']", "user@example.com", "Need to fill this.")
        engine = PersonaEngine(llm_client=client)
        result = engine.decide_next_action(PERSONA_BUSY_MOM, self.state, DOM_STATE)
        assert result["action"] == "fill"
        assert result["value"] == "user@example.com"

    def test_valid_action_dropout_is_parsed(self):
        client = _make_mock_client("dropout", "", "", "Too confusing, giving up.")
        engine = PersonaEngine(llm_client=client)
        result = engine.decide_next_action(PERSONA_BUSY_MOM, self.state, DOM_STATE)
        assert result["action"] == "dropout"

    @pytest.mark.parametrize("action", ["scroll", "wait"])
    def test_all_valid_actions_are_accepted(self, action):
        client = _make_mock_client(action)
        engine = PersonaEngine(llm_client=client)
        result = engine.decide_next_action(PERSONA_TECH_MILLENNIAL, self.state, DOM_STATE)
        assert result["action"] == action

    def test_invalid_action_raises_value_error(self):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_llm_response("hover")
        engine = PersonaEngine(llm_client=client)
        with pytest.raises(ValueError, match="unknown action"):
            engine.decide_next_action(PERSONA_BUSY_MOM, self.state, DOM_STATE)

    def test_malformed_json_raises_value_error(self):
        choice = MagicMock()
        choice.message.content = "not json at all"
        response = MagicMock()
        response.choices = [choice]
        client = MagicMock()
        client.chat.completions.create.return_value = response
        engine = PersonaEngine(llm_client=client)
        with pytest.raises(ValueError, match="invalid JSON"):
            engine.decide_next_action(PERSONA_BUSY_MOM, self.state, DOM_STATE)

    def test_thought_process_is_included_in_result(self):
        thought = "The CTA is prominent and matches my goal."
        client = _make_mock_client("click", "button.cta", "", thought)
        engine = PersonaEngine(llm_client=client)
        result = engine.decide_next_action(PERSONA_BUSY_MOM, self.state, DOM_STATE)
        assert result["thought_process"] == thought

    def test_llm_is_called_with_persona_name_in_prompt(self):
        client = _make_mock_client()
        engine = PersonaEngine(llm_client=client)
        engine.decide_next_action(PERSONA_BUSY_MOM, self.state, DOM_STATE)
        call_args = client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args.args[0] if call_args.args else call_args.kwargs["messages"]
        user_content = next(
            m["content"] for m in messages if m["role"] == "user"
        )
        assert "Busy Mom" in user_content

    def test_no_screenshot_sends_text_only_message(self):
        client = _make_mock_client()
        engine = PersonaEngine(llm_client=client)
        engine.decide_next_action(PERSONA_BUSY_MOM, self.state, DOM_STATE, screenshot_path=None)
        call_args = client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args.kwargs["messages"]
        user_msg = next(m for m in messages if m["role"] == "user")
        assert isinstance(user_msg["content"], str)


# ---------------------------------------------------------------------------
# Bias injection tests
# ---------------------------------------------------------------------------

class TestBiasInjection:
    def setup_method(self):
        self.engine = PersonaEngine()

    def test_known_biases_produce_behavioural_hints(self):
        biases = ["loss aversion", "status quo bias"]
        result = self.engine._format_bias_instructions(biases)
        assert "loss aversion" in result.lower()
        assert "status quo bias" in result.lower()
        assert "Prefer familiar options" in result

    def test_unknown_bias_falls_back_gracefully(self):
        result = self.engine._format_bias_instructions(["novelty seeking"])
        assert "novelty seeking" in result

    def test_no_biases_returns_placeholder(self):
        result = self.engine._format_bias_instructions([])
        assert "No strongly expressed biases" in result

    def test_all_fixture_biases_have_known_hints(self):
        all_biases = (
            PERSONA_BUSY_MOM.cognitive_biases
            + PERSONA_TECH_MILLENNIAL.cognitive_biases
            + PERSONA_SENIOR_SHOPPER.cognitive_biases
        )
        for bias in all_biases:
            assert bias.lower() in _BIAS_BEHAVIORAL_HINTS, (
                f"Bias '{bias}' has no entry in _BIAS_BEHAVIORAL_HINTS"
            )

    def test_decision_prompt_contains_bias_hints(self):
        state = PersonaState()
        prompt = self.engine._build_decision_prompt(PERSONA_BUSY_MOM, state, DOM_STATE)
        assert "loss aversion" in prompt.lower()
        assert "status quo bias" in prompt.lower()

    def test_decision_prompt_contains_state_values(self):
        state = PersonaState(remaining_patience=0.5, current_motivation=0.8, confusion_level=0.2)
        prompt = self.engine._build_decision_prompt(PERSONA_BUSY_MOM, state, DOM_STATE)
        assert "50%" in prompt
        assert "80%" in prompt
        assert "20%" in prompt


# ---------------------------------------------------------------------------
# State update tests
# ---------------------------------------------------------------------------

class TestUpdateState:
    def setup_method(self):
        self.engine = PersonaEngine()
        self.initial_state = PersonaState()
        self.click_action = {
            "action": "click",
            "selector": "button.cta",
            "value": "",
            "thought_process": "This looks right.",
        }

    def test_action_is_appended_to_history(self):
        new_state = self.engine.update_state(self.initial_state, self.click_action)
        assert len(new_state.execution_history) == 1
        assert new_state.execution_history[0] == self.click_action

    def test_patience_decreases_after_each_step(self):
        new_state = self.engine.update_state(self.initial_state, self.click_action)
        assert new_state.remaining_patience < self.initial_state.remaining_patience

    def test_high_cls_decreases_patience_more(self):
        low_friction = self.engine.update_state(
            self.initial_state, self.click_action, evaluation={"composite_cls": 10}
        )
        high_friction = self.engine.update_state(
            self.initial_state, self.click_action, evaluation={"composite_cls": 90}
        )
        assert high_friction.remaining_patience < low_friction.remaining_patience

    def test_high_cls_increases_confusion(self):
        new_state = self.engine.update_state(
            self.initial_state, self.click_action, evaluation={"composite_cls": 90}
        )
        assert new_state.confusion_level > self.initial_state.confusion_level

    def test_low_cls_reduces_confusion(self):
        confused_state = PersonaState(confusion_level=0.5)
        new_state = self.engine.update_state(
            confused_state, self.click_action, evaluation={"composite_cls": 10}
        )
        assert new_state.confusion_level < confused_state.confusion_level

    def test_dropout_action_reduces_motivation_sharply(self):
        dropout_action = {**self.click_action, "action": "dropout"}
        new_state = self.engine.update_state(self.initial_state, dropout_action)
        assert new_state.current_motivation < 0.6

    def test_state_values_stay_in_bounds(self):
        state = PersonaState(remaining_patience=0.01, confusion_level=0.99)
        # Many high-friction steps should clamp, not overflow.
        for _ in range(10):
            state = self.engine.update_state(state, self.click_action, evaluation={"composite_cls": 100})
        assert 0.0 <= state.remaining_patience <= 1.0
        assert 0.0 <= state.confusion_level <= 1.0
        assert 0.0 <= state.current_motivation <= 1.0

    def test_original_state_is_not_mutated(self):
        original_history = list(self.initial_state.execution_history)
        self.engine.update_state(self.initial_state, self.click_action)
        assert self.initial_state.execution_history == original_history
