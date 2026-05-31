from __future__ import annotations

from typing import Any

from src.evaluation.models import FrictionPoint, StepEvaluationResult

_CTA_KEYWORDS = (
    "buy",
    "sign up",
    "get started",
    "subscribe",
    "checkout",
    "add to cart",
    "shop now",
    "order",
)


class CognitiveEvaluationEngine:
    def __init__(self, use_llm: bool = False, api_key: str | None = None):
        if use_llm:
            raise NotImplementedError("LLM evaluation is not available in M1.")
        self.use_llm = use_llm
        self.api_key = api_key

    def evaluate_step(
        self, dom_state: dict[str, Any], persona_constraints: dict[str, Any]
    ) -> StepEvaluationResult:
        elements = dom_state.get("elements", [])
        visual = self._visual_complexity_score(len(elements))
        interaction = self._interaction_friction_score(elements)
        tolerance = int(persona_constraints.get("complexity_tolerance", 3))
        alignment = self._cognitive_alignment_score(visual, tolerance)
        friction_points = self.identify_friction_points(dom_state)
        composite = self._composite_cls(visual, interaction, alignment)

        return StepEvaluationResult(
            visual_complexity_score=visual,
            interaction_friction_score=interaction,
            cognitive_alignment_score=alignment,
            composite_cls=composite,
            identified_friction_points=friction_points,
        )

    def identify_friction_points(self, dom_state: dict[str, Any]) -> list[FrictionPoint]:
        elements = dom_state.get("elements", [])
        points: list[FrictionPoint] = []

        if not self._has_primary_cta(elements):
            points.append(
                FrictionPoint(
                    severity="high",
                    description="No primary call-to-action button detected on the page.",
                    recommendation="Add a clearly labeled primary CTA (e.g., Buy Now or Sign Up).",
                )
            )

        unlabeled_inputs = [
            el
            for el in elements
            if el.get("tag") == "input"
            and not (el.get("aria_label") or "").strip()
            and not (el.get("text") or "").strip()
        ]
        if unlabeled_inputs:
            points.append(
                FrictionPoint(
                    severity="medium",
                    description=f"{len(unlabeled_inputs)} form field(s) lack accessible labels.",
                    recommendation="Associate inputs with <label> elements or aria-label attributes.",
                )
            )

        long_text_blocks = [
            el
            for el in elements
            if el.get("tag") in ("p", "div", "span")
            and len((el.get("text") or "")) > 300
        ]
        if len(long_text_blocks) >= 3:
            points.append(
                FrictionPoint(
                    severity="low",
                    description="Multiple large text blocks may increase cognitive load.",
                    recommendation="Break content into scannable sections with headings and bullets.",
                )
            )

        inaccessible_ratio = self._inaccessible_element_ratio(elements)
        if inaccessible_ratio > 0.5 and elements:
            points.append(
                FrictionPoint(
                    severity="medium",
                    description="Many interactive elements lack visible text or aria labels.",
                    recommendation="Ensure buttons and links have descriptive text or aria-label values.",
                )
            )

        return points

    def _visual_complexity_score(self, element_count: int) -> int:
        if element_count > 50:
            return min(100, 80 + (element_count - 50))
        if element_count >= 20:
            span = max(1, 50 - 20)
            offset = element_count - 20
            return 40 + min(39, (offset * 39) // span)
        if element_count <= 0:
            return 10
        return 10 + min(29, (element_count * 29) // 19)

    def _interaction_friction_score(self, elements: list[dict[str, Any]]) -> int:
        if not elements:
            return 50

        inaccessible = sum(
            1
            for el in elements
            if not (el.get("aria_label") or "").strip()
            and not (el.get("text") or "").strip()
        )
        ratio = inaccessible / len(elements)
        score = int(round(ratio * 70))

        if not self._has_primary_cta(elements):
            score = min(100, score + 25)

        return max(1, min(100, score))

    def _cognitive_alignment_score(
        self, visual_complexity: int, complexity_tolerance: int
    ) -> int:
        tolerance = max(1, min(5, complexity_tolerance))
        acceptable_max = tolerance * 20
        if visual_complexity <= acceptable_max:
            return 100
        excess = visual_complexity - acceptable_max
        return max(1, 100 - excess * 2)

    def _composite_cls(
        self,
        visual: int,
        interaction: int,
        alignment: int,
    ) -> int:
        raw = (
            0.35 * visual
            + 0.40 * interaction
            + 0.25 * (100 - alignment)
        )
        return max(1, min(100, int(round(raw))))

    def _has_primary_cta(self, elements: list[dict[str, Any]]) -> bool:
        for el in elements:
            if el.get("tag") not in ("button", "a"):
                continue
            text = (el.get("text") or "").lower()
            aria = (el.get("aria_label") or "").lower()
            combined = f"{text} {aria}"
            if any(keyword in combined for keyword in _CTA_KEYWORDS):
                return True
        return False

    def _inaccessible_element_ratio(self, elements: list[dict[str, Any]]) -> float:
        interactive = [
            el
            for el in elements
            if el.get("tag") in ("button", "input", "a", "select", "textarea")
        ]
        if not interactive:
            return 0.0
        inaccessible = sum(
            1
            for el in interactive
            if not (el.get("aria_label") or "").strip()
            and not (el.get("text") or "").strip()
        )
        return inaccessible / len(interactive)
