from __future__ import annotations

import json
import os
from typing import Any

from .models import PersonaProfile, PersonaState

# ---------------------------------------------------------------------------
# Cognitive-bias behavioural hint library
# ---------------------------------------------------------------------------

_BIAS_BEHAVIORAL_HINTS: dict[str, str] = {
    "loss aversion": (
        "You are highly sensitive to perceived losses. "
        "Prefer familiar options and avoid changes that feel risky or irreversible."
    ),
    "status quo bias": (
        "You strongly prefer the default or current state. "
        "Only deviate from existing patterns when a benefit is obviously clear."
    ),
    "social proof": (
        "You seek reassurance from others. "
        "Look for reviews, ratings, 'popular choice' badges, or user counts before committing."
    ),
    "authority bias": (
        "You trust official-looking elements, expert endorsements, certifications, "
        "and authoritative language (e.g., 'Verified', 'Recommended by experts')."
    ),
    "anchoring": (
        "The first piece of information you encounter heavily anchors your expectations. "
        "Compare every subsequent price or option against that first number."
    ),
    "confirmation bias": (
        "You seek out information that confirms your pre-existing beliefs "
        "and tend to overlook contradictory signals."
    ),
    "scarcity heuristic": (
        "Limited-time offers and low-stock warnings create urgency that drives your decisions, "
        "even if you were not planning to act quickly."
    ),
}


class PersonaEngine:
    """Builds deterministic prompts and cognitive constraints for personas.

    Pass an optional *llm_client* (e.g. an ``openai.OpenAI`` instance) to
    control which backend is used for :meth:`decide_next_action`.  When
    *llm_client* is ``None`` the engine lazily constructs a default
    ``openai.OpenAI()`` client on first use.
    """

    def __init__(self, llm_client: Any = None) -> None:
        self._llm_client = llm_client

    # ------------------------------------------------------------------
    # Public API — system prompt & constraints (unchanged from M1)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Public API — LLM action decision (M2)
    # ------------------------------------------------------------------

    def decide_next_action(
        self,
        profile: PersonaProfile,
        state: PersonaState,
        dom_state: dict,
        screenshot_path: str | None = None,
    ) -> dict:
        """Ask the LLM to choose the persona's next interaction step.

        Parameters
        ----------
        profile:
            The static demographic/cognitive profile of the persona.
        state:
            The dynamic cognitive state accumulated so far in this run.
        dom_state:
            Dictionary describing the current page (keys: ``current_url``,
            ``elements``, etc.).
        screenshot_path:
            Optional path to a PNG screenshot.  When provided and the file
            exists the image is included in the LLM request as a vision input.

        Returns
        -------
        dict
            Structured action with keys: ``action``, ``selector``, ``value``,
            ``thought_process``.
        """
        client = self._get_llm_client()
        prompt = self._build_decision_prompt(profile, state, dom_state)
        raw = self._call_llm(client, prompt, screenshot_path)
        return self._parse_action_response(raw)

    def update_state(
        self,
        state: PersonaState,
        action: dict,
        evaluation: dict | None = None,
    ) -> PersonaState:
        """Return a new :class:`PersonaState` updated after one interaction step.

        Parameters
        ----------
        state:
            The state *before* the action.
        action:
            The action dict returned by :meth:`decide_next_action`.
        evaluation:
            Optional evaluation result dict (e.g. containing ``composite_cls``).
            When provided the CLS score drives patience/confusion deltas.
        """
        cls_score: int = (evaluation or {}).get("composite_cls", 40)

        # Patience decreases more when friction is high.
        friction_ratio = max(0.0, min(1.0, cls_score / 100.0))
        patience_delta = -0.05 - 0.15 * friction_ratio
        new_patience = max(0.0, state.remaining_patience + patience_delta)

        # Motivation takes a small hit on every step; dropout halves it.
        motivation_delta = -0.02 if action.get("action") != "dropout" else -0.50
        new_motivation = max(0.0, state.current_motivation + motivation_delta)

        # Confusion rises with high CLS and falls slightly on each clear action.
        confusion_delta = 0.10 * friction_ratio - 0.02
        new_confusion = max(0.0, min(1.0, state.confusion_level + confusion_delta))

        new_history = state.execution_history + [action]

        return PersonaState(
            remaining_patience=round(new_patience, 4),
            current_motivation=round(new_motivation, 4),
            confusion_level=round(new_confusion, 4),
            execution_history=new_history,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_llm_client(self) -> Any:
        if self._llm_client is not None:
            return self._llm_client
        try:
            import openai  # noqa: PLC0415
            return openai.OpenAI()
        except ImportError as exc:
            raise ImportError(
                "openai package is required for LLM-based decisions. "
                "Install it with: pip install openai"
            ) from exc

    def _build_decision_prompt(
        self,
        profile: PersonaProfile,
        state: PersonaState,
        dom_state: dict,
    ) -> str:
        bias_block = self._format_bias_instructions(profile.cognitive_biases)
        history_block = self._format_history(state.execution_history)
        elements_block = json.dumps(dom_state.get("elements", []), indent=2)
        current_url = dom_state.get("current_url", "unknown")

        patience_pct = round(state.remaining_patience * 100)
        motivation_pct = round(state.current_motivation * 100)
        confusion_pct = round(state.confusion_level * 100)

        return (
            f"You are simulating {profile.name}, age {profile.age}, "
            f"tech savviness {profile.tech_savviness}/5, "
            f"motivation level {profile.motivation_level}/5.\n\n"
            "## Cognitive State\n"
            f"- Remaining patience: {patience_pct}%\n"
            f"- Current motivation: {motivation_pct}%\n"
            f"- Confusion level: {confusion_pct}%\n\n"
            "## Active Cognitive Biases\n"
            f"{bias_block}\n\n"
            "## Current Page\n"
            f"URL: {current_url}\n\n"
            "## Visible Elements\n"
            f"{elements_block}\n\n"
            "## Interaction History\n"
            f"{history_block}\n\n"
            "## Task\n"
            "Based on the above context, decide the single best next action for this persona. "
            "Consider the persona's patience and confusion: if patience is below 20% or "
            "confusion is above 80%, lean towards dropout.\n\n"
            "Respond ONLY with a valid JSON object (no markdown, no extra text) containing:\n"
            '  "action": one of "click", "fill", "scroll", "wait", "dropout"\n'
            '  "selector": CSS selector of the target element (empty string if not applicable)\n'
            '  "value": text to fill in (empty string if not applicable)\n'
            '  "thought_process": one sentence explaining this persona\'s cognitive reasoning\n'
        )

    def _format_bias_instructions(self, biases: list[str]) -> str:
        if not biases:
            return "- No strongly expressed biases."
        lines = []
        for bias in biases:
            hint = _BIAS_BEHAVIORAL_HINTS.get(bias.lower(), f"You exhibit {bias}.")
            lines.append(f"- **{bias}**: {hint}")
        return "\n".join(lines)

    def _format_history(self, history: list[dict]) -> str:
        if not history:
            return "No actions taken yet."
        lines = []
        for i, entry in enumerate(history[-5:], 1):
            action = entry.get("action", "unknown")
            selector = entry.get("selector", "")
            thought = entry.get("thought_process", "")
            line = f"{i}. {action}"
            if selector:
                line += f" \u2192 {selector}"
            if thought:
                line += f' ("{thought}")'
            lines.append(line)
        return "\n".join(lines)

    def _call_llm(self, client: Any, prompt: str, screenshot_path: str | None) -> str:
        """Send the decision prompt to the LLM and return the raw response string."""
        messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "You are a UX simulation engine. "
                    "Always respond with valid JSON only — no markdown, no extra explanation."
                ),
            },
        ]

        if screenshot_path and os.path.isfile(screenshot_path):
            import base64  # noqa: PLC0415
            with open(screenshot_path, "rb") as fh:
                img_b64 = base64.b64encode(fh.read()).decode()
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    },
                ],
            })
        else:
            messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    def _parse_action_response(self, raw: str) -> dict:
        """Parse and validate the JSON string returned by the LLM."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned invalid JSON: {raw!r}") from exc

        valid_actions = {"click", "fill", "scroll", "wait", "dropout"}
        action = data.get("action", "")
        if action not in valid_actions:
            raise ValueError(
                f"LLM returned unknown action {action!r}. "
                f"Must be one of: {sorted(valid_actions)}"
            )

        return {
            "action": action,
            "selector": str(data.get("selector", "")),
            "value": str(data.get("value", "")),
            "thought_process": str(data.get("thought_process", "")),
        }

    def _derive_complexity_tolerance(self, profile: PersonaProfile) -> int:
        return max(1, min(5, round((profile.tech_savviness + profile.motivation_level) / 2)))

    def _derive_dropout_threshold(self, profile: PersonaProfile, complexity_tolerance: int) -> int:
        threshold = 35 + (complexity_tolerance * 8) + (profile.motivation_level * 5)
        return max(40, min(95, threshold))
