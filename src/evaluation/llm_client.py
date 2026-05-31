from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

import requests


class OpenAIVisionEvaluationClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gpt-4.1-mini",
        endpoint: str = "https://api.openai.com/v1/chat/completions",
        timeout_seconds: int = 30,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "LLM evaluation requires an API key via api_key or OPENAI_API_KEY."
            )
        self.model = model
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def analyze_step(
        self,
        *,
        screenshot_path: str | None,
        dom_state: dict[str, Any],
        persona_constraints: dict[str, Any],
    ) -> dict[str, Any]:
        if not screenshot_path:
            raise ValueError("LLM evaluation requires a screenshot_path.")

        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": self._system_prompt()},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": self._user_prompt(
                                    dom_state=dom_state,
                                    persona_constraints=persona_constraints,
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": self._encode_screenshot(screenshot_path)
                                },
                            },
                        ],
                    },
                ],
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return self._parse_response(response.json())

    def _system_prompt(self) -> str:
        return (
            "You are a visual UX audit engine. Analyze the screenshot and DOM "
            "summary for visual complexity, interaction friction, and cognitive "
            "alignment. Return only JSON with integer scores from 1 to 100 for "
            "visual_complexity_score, interaction_friction_score, and "
            "cognitive_alignment_score, plus identified_friction_points as an "
            "array of objects with severity, description, and recommendation. "
            "Use severities low, medium, high, or critical. Identify issues such "
            "as poor contrast, cluttered layout, hidden CTAs, unclear labels, "
            "and small tap targets. Include visual location details in the "
            "description when useful, but do not add fields outside the schema. "
            "Do not compute composite_cls; the application computes it."
        )

    def _user_prompt(
        self,
        *,
        dom_state: dict[str, Any],
        persona_constraints: dict[str, Any],
    ) -> str:
        payload = {
            "persona_constraints": persona_constraints,
            "dom_summary": self._summarize_dom(dom_state),
            "scoring_guidance": {
                "visual_complexity_score": "Higher means denser or harder to scan.",
                "interaction_friction_score": "Higher means harder to complete the next action.",
                "cognitive_alignment_score": (
                    "Higher means better fit for the persona constraints."
                ),
            },
        }
        return json.dumps(payload, ensure_ascii=True)

    def _encode_screenshot(self, screenshot_path: str) -> str:
        path = Path(screenshot_path)
        mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _parse_response(self, response_json: dict[str, Any]) -> dict[str, Any]:
        content = response_json["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        if not isinstance(content, str):
            raise ValueError("LLM response content must be a JSON string.")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response JSON must be an object.")
        return parsed

    def _summarize_dom(self, dom_state: dict[str, Any]) -> list[dict[str, Any]]:
        elements = dom_state.get("elements", [])
        summary: list[dict[str, Any]] = []
        for element in elements[:100]:
            summary.append(
                {
                    "tag": element.get("tag", ""),
                    "text": self._truncate(element.get("text", "")),
                    "aria_label": self._truncate(element.get("aria_label", "")),
                    "href": self._truncate(element.get("href", ""), limit=120),
                    "bounding_box": element.get("bounding_box"),
                }
            )
        return summary

    def _truncate(self, value: Any, *, limit: int = 200) -> str:
        text = str(value or "")
        if len(text) <= limit:
            return text
        return f"{text[: limit - 3]}..."
