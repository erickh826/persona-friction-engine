from src.persona.engine import PersonaEngine
from src.persona.fixtures import (
    PERSONA_BUSY_MOM,
    PERSONA_SENIOR_SHOPPER,
    PERSONA_TECH_MILLENNIAL,
)


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
