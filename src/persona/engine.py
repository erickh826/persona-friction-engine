from __future__ import annotations

from .models import PersonaProfile


class PersonaEngine:
    """Builds deterministic prompts and cognitive constraints for personas."""

    def get_system_prompt(self, profile: PersonaProfile) -> str:
        """Return a system prompt that instructs an LLM to behave as the persona."""
        bias_list = ", ".join(profile.cognitive_biases) if profile.cognitive_biases else "no strongly expressed biases"
        complexity_tolerance = self._derive_complexity_tolerance(profile)
        constraints = self.get_cognitive_constraints(profile)

        return (
            "You are simulating a real user for a usability test. "
            f"Adopt the persona of {profile.name}, age {profile.age}, with tech savviness "
            f"{profile.tech_savviness}/5 and motivation level {profile.motivation_level}/5. "
            f"This persona has an attention span of about {profile.attention_span_seconds} seconds, "
            f"a complexity tolerance of {complexity_tolerance}/5, and cognitive biases including {bias_list}. "
            "Behave consistently with this persona: prefer actions that match their technical comfort, "
            "avoid leaps of knowledge they would not realistically make, and show hesitation when an interface "
            "is overly dense or confusing. Keep responses grounded in the persona's goal, move step by step, "
            "and stop when the task becomes too cognitively taxing. "
            f"Do not exceed roughly {constraints['max_steps']} meaningful interaction steps before reevaluating. "
            f"If perceived friction rises above a dropout threshold of {constraints['dropout_threshold']}, "
            "respond as a user who is likely to abandon the flow."
        )

    def get_cognitive_constraints(self, profile: PersonaProfile) -> dict:
        """Return deterministic navigation constraints derived from a persona profile."""
        max_steps = max(1, profile.attention_span_seconds // 30)
        complexity_tolerance = self._derive_complexity_tolerance(profile)
        dropout_threshold = self._derive_dropout_threshold(profile, complexity_tolerance)

        return {
            "max_steps": max_steps,
            "complexity_tolerance": complexity_tolerance,
            "dropout_threshold": dropout_threshold,
        }

    def _derive_complexity_tolerance(self, profile: PersonaProfile) -> int:
        return max(1, min(5, round((profile.tech_savviness + profile.motivation_level) / 2)))

    def _derive_dropout_threshold(self, profile: PersonaProfile, complexity_tolerance: int) -> int:
        threshold = 35 + (complexity_tolerance * 8) + (profile.motivation_level * 5)
        return max(40, min(95, threshold))
