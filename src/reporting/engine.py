from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any


_SEVERITY_STYLES = {
    "critical": {
        "badge": "bg-red-100 text-red-800 border-red-200",
        "border": "border-red-500",
        "dot": "bg-red-600",
    },
    "high": {
        "badge": "bg-orange-100 text-orange-800 border-orange-200",
        "border": "border-orange-500",
        "dot": "bg-orange-500",
    },
    "medium": {
        "badge": "bg-amber-100 text-amber-800 border-amber-200",
        "border": "border-amber-500",
        "dot": "bg-amber-500",
    },
    "low": {
        "badge": "bg-blue-100 text-blue-800 border-blue-200",
        "border": "border-blue-500",
        "dot": "bg-blue-500",
    },
}


class ReportingEngine:
    """Generate a static interactive HTML report for a completed audit run."""

    def generate_html_report(self, run_result: dict[str, Any], output_path: str) -> str:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.render_html(run_result), encoding="utf-8")
        return str(output)

    def render_html(self, run_result: dict[str, Any]) -> str:
        steps = self._steps(run_result)
        chart_payload = self._chart_payload(run_result, steps)
        scenario_id = self._text(run_result.get("scenario_id", "unknown-scenario"))
        dropout = bool(run_result.get("dropout", False))
        dropout_text = (
            self._text(run_result.get("dropout_reason", "Dropout detected."))
            if dropout
            else "No dropout detected"
        )

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Persona Friction Audit: {scenario_id}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased">
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
    <header class="rounded-3xl border border-slate-800 bg-slate-900/90 p-8 shadow-2xl shadow-slate-950/40">
      <p class="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-300">Persona Friction Engine</p>
      <div class="mt-4 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 class="text-4xl font-bold tracking-tight text-white">Interactive UX Audit Report</h1>
          <p class="mt-3 max-w-3xl text-slate-300">{self._text(run_result.get("target_goal", "UX friction audit"))}</p>
        </div>
        <div class="rounded-2xl border border-cyan-400/30 bg-cyan-400/10 px-6 py-4 text-center">
          <p class="text-xs uppercase tracking-widest text-cyan-200">Final CLS</p>
          <p class="text-5xl font-black text-white">{self._number(run_result.get("final_cls", 0))}</p>
        </div>
      </div>
      {self._summary_cards(run_result, dropout_text)}
    </header>

    <section class="mt-8 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <article class="rounded-3xl border border-slate-800 bg-slate-900 p-6">
        <div class="flex items-center justify-between gap-4">
          <div>
            <h2 class="text-2xl font-bold text-white">CLS Progression</h2>
            <p class="text-sm text-slate-400">Composite load score across simulation steps.</p>
          </div>
          <span class="rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-300">{len(steps)} steps</span>
        </div>
        <div class="mt-6 h-80">
          <canvas id="clsChart" aria-label="CLS progression chart"></canvas>
        </div>
      </article>

      <article class="rounded-3xl border border-slate-800 bg-slate-900 p-6">
        <h2 class="text-2xl font-bold text-white">Severity Mix</h2>
        <p class="text-sm text-slate-400">Friction points grouped by severity.</p>
        <div class="mt-6 grid grid-cols-2 gap-4">
          {self._severity_summary(steps)}
        </div>
        <div class="mt-6 rounded-2xl border {'border-red-500/60 bg-red-500/10' if dropout else 'border-emerald-500/40 bg-emerald-500/10'} p-4">
          <p class="text-sm font-semibold uppercase tracking-widest {'text-red-200' if dropout else 'text-emerald-200'}">Dropout Status</p>
          <p class="mt-2 text-sm text-slate-200">{dropout_text}</p>
        </div>
      </article>
    </section>

    <section class="mt-8 rounded-3xl border border-slate-800 bg-slate-900 p-6">
      <h2 class="text-2xl font-bold text-white">Step Timeline</h2>
      <div class="mt-6 space-y-6">
        {self._timeline_html(steps)}
      </div>
    </section>
  </main>

  <script id="report-data" type="application/json">{self._json_script(chart_payload)}</script>
  <script>
    const reportData = JSON.parse(document.getElementById("report-data").textContent);
    const dropoutStep = reportData.dropoutStep;
    const pointBackground = reportData.labels.map((label) => label === dropoutStep ? "#ef4444" : "#22d3ee");
    new Chart(document.getElementById("clsChart"), {{
      type: "line",
      data: {{
        labels: reportData.labels,
        datasets: [{{
          label: "Composite CLS",
          data: reportData.clsScores,
          borderColor: "#22d3ee",
          backgroundColor: "rgba(34, 211, 238, 0.16)",
          pointBackgroundColor: pointBackground,
          pointBorderColor: "#ffffff",
          pointRadius: 6,
          tension: 0.35,
          fill: true
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          y: {{ min: 0, max: 100, grid: {{ color: "rgba(148, 163, 184, 0.18)" }}, ticks: {{ color: "#cbd5e1" }} }},
          x: {{ grid: {{ color: "rgba(148, 163, 184, 0.12)" }}, ticks: {{ color: "#cbd5e1" }} }}
        }},
        plugins: {{
          legend: {{ labels: {{ color: "#e2e8f0" }} }},
          tooltip: {{ callbacks: {{ afterLabel: (context) => context.label === dropoutStep ? "Dropout point" : "" }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""

    def _summary_cards(self, run_result: dict[str, Any], dropout_text: str) -> str:
        cards = [
            ("Scenario", run_result.get("scenario_id", "unknown")),
            ("Target", run_result.get("target_url", "")),
            ("Persona", run_result.get("persona_name", "Unknown")),
            ("Total Steps", run_result.get("total_steps", len(self._steps(run_result)))),
            ("Duration", f"{run_result.get('execution_time_seconds', 0)}s"),
            ("Dropout", dropout_text),
        ]
        return "<div class=\"mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3\">" + "".join(
            f"""
        <div class="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
          <p class="text-xs font-semibold uppercase tracking-widest text-slate-500">{self._text(label)}</p>
          <p class="mt-2 truncate text-sm text-slate-100" title="{self._text(value)}">{self._text(value)}</p>
        </div>"""
            for label, value in cards
        ) + "\n      </div>"

    def _timeline_html(self, steps: list[dict[str, Any]]) -> str:
        if not steps:
            return "<p class=\"rounded-2xl border border-slate-800 p-4 text-slate-400\">No steps recorded.</p>"

        return "".join(self._step_card(step) for step in steps)

    def _step_card(self, step: dict[str, Any]) -> str:
        step_number = self._text(step.get("step_number", "?"))
        cls = self._number(step.get("composite_cls", 0))
        current_url = self._text(step.get("current_url", ""))
        action = self._text(step.get("action_taken", "unknown"))
        screenshot = self._text(step.get("screenshot_path", ""))
        friction_points = step.get("identified_friction_points", []) or []
        highest = self._highest_severity(friction_points)
        style = _SEVERITY_STYLES[highest]

        screenshot_html = ""
        if screenshot:
            screenshot_html = f"""
          <div class="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
            <img src="{screenshot}" alt="Screenshot for step {step_number}" class="w-full object-contain">
            {self._overlay_html(friction_points)}
          </div>"""

        return f"""
        <article class="relative border-l-4 {style['border']} pl-6">
          <div class="absolute -left-[11px] top-1 h-5 w-5 rounded-full border-4 border-slate-900 {style['dot']}"></div>
          <div class="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p class="text-sm font-semibold uppercase tracking-widest text-slate-500">Step {step_number}</p>
                <h3 class="mt-1 text-xl font-bold text-white">CLS {cls}</h3>
                <p class="mt-2 break-all text-sm text-slate-400">{current_url}</p>
                <p class="mt-1 text-sm text-slate-500">Action: {action}</p>
              </div>
              <div class="grid grid-cols-3 gap-3 text-center">
                {self._metric_pill("Visual", step.get("visual_complexity_score", 0))}
                {self._metric_pill("Friction", step.get("interaction_friction_score", 0))}
                {self._metric_pill("Alignment", step.get("cognitive_alignment_score", 0))}
              </div>
            </div>
            <div class="mt-5 grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
              {screenshot_html}
              <div>
                <h4 class="font-semibold text-white">Friction Points Inspector</h4>
                <div class="mt-3 space-y-3">
                  {self._friction_points_html(friction_points)}
                </div>
              </div>
            </div>
          </div>
        </article>"""

    def _metric_pill(self, label: str, value: Any) -> str:
        return f"""
                <div class="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-3">
                  <p class="text-xs uppercase tracking-widest text-slate-500">{self._text(label)}</p>
                  <p class="mt-1 text-2xl font-black text-white">{self._number(value)}</p>
                </div>"""

    def _friction_points_html(self, friction_points: list[dict[str, Any]]) -> str:
        if not friction_points:
            return "<p class=\"rounded-2xl border border-slate-800 p-4 text-sm text-slate-400\">No friction points identified.</p>"

        html = []
        for point in friction_points:
            severity = self._severity(point.get("severity", "low"))
            style = _SEVERITY_STYLES[severity]
            description = self._text(point.get("description", "No description provided."))
            recommendation = self._text(point.get("recommendation", "No recommendation provided."))
            coordinate_note = self._coordinate_note(point)
            html.append(
                f"""
                  <div class="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                    <span class="inline-flex rounded-full border px-2.5 py-1 text-xs font-bold uppercase tracking-widest {style['badge']}">{severity}</span>
                    <p class="mt-3 text-sm text-slate-100">{description}</p>
                    <p class="mt-2 text-sm text-cyan-200">Recommendation: {recommendation}</p>
                    {coordinate_note}
                  </div>"""
            )
        return "".join(html)

    def _overlay_html(self, friction_points: list[dict[str, Any]]) -> str:
        overlays = []
        for point in friction_points:
            box = self._coordinates(point)
            if box is None:
                continue
            severity = self._severity(point.get("severity", "low"))
            color = {
                "critical": "border-red-500 bg-red-500/20",
                "high": "border-orange-500 bg-orange-500/20",
                "medium": "border-amber-400 bg-amber-400/20",
                "low": "border-blue-400 bg-blue-400/20",
            }[severity]
            overlays.append(
                f"""<div class="absolute border-2 {color}" style="left:{self._format_percent(box['x'])}%; top:{self._format_percent(box['y'])}%; width:{self._format_percent(box['width'])}%; height:{self._format_percent(box['height'])}%;" title="{self._text(point.get('description', 'Friction point'))}"></div>"""
            )
        return "\n            ".join(overlays)

    def _severity_summary(self, steps: list[dict[str, Any]]) -> str:
        counts = {severity: 0 for severity in _SEVERITY_STYLES}
        for step in steps:
            for point in step.get("identified_friction_points", []) or []:
                counts[self._severity(point.get("severity", "low"))] += 1

        return "".join(
            f"""
          <div class="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <p class="text-xs font-semibold uppercase tracking-widest text-slate-500">{severity}</p>
            <p class="mt-2 text-3xl font-black text-white">{count}</p>
          </div>"""
            for severity, count in counts.items()
        )

    def _chart_payload(
        self, run_result: dict[str, Any], steps: list[dict[str, Any]]
    ) -> dict[str, Any]:
        dropout_step = None
        if run_result.get("dropout") and steps:
            dropout_step = f"Step {steps[-1].get('step_number', len(steps))}"
        return {
            "labels": [f"Step {step.get('step_number', index + 1)}" for index, step in enumerate(steps)],
            "clsScores": [self._number(step.get("composite_cls", 0)) for step in steps],
            "dropoutStep": dropout_step,
        }

    def _steps(self, run_result: dict[str, Any]) -> list[dict[str, Any]]:
        return list(run_result.get("steps", []) or [])

    def _highest_severity(self, friction_points: list[dict[str, Any]]) -> str:
        order = ["low", "medium", "high", "critical"]
        highest = "low"
        for point in friction_points:
            severity = self._severity(point.get("severity", "low"))
            if order.index(severity) > order.index(highest):
                highest = severity
        return highest

    def _coordinate_note(self, point: dict[str, Any]) -> str:
        box = self._coordinates(point)
        if box is None:
            return ""
        return (
            '<p class="mt-2 text-xs text-slate-500">'
            f"Overlay: x={self._format_percent(box['x'])}%, y={self._format_percent(box['y'])}%, width={self._format_percent(box['width'])}%, height={self._format_percent(box['height'])}%"
            "</p>"
        )

    def _coordinates(self, point: dict[str, Any]) -> dict[str, float] | None:
        raw = point.get("coordinates") or point.get("bounding_box")
        if not isinstance(raw, dict):
            return None

        try:
            x = float(raw.get("x", raw.get("left", 0)))
            y = float(raw.get("y", raw.get("top", 0)))
            width = float(raw.get("width", 0))
            height = float(raw.get("height", 0))
        except (TypeError, ValueError):
            return None

        if width <= 0 or height <= 0:
            return None

        if max(x, y, width, height) > 100:
            image_width = float(raw.get("image_width", raw.get("viewport_width", 1440)))
            image_height = float(raw.get("image_height", raw.get("viewport_height", 900)))
            if image_width <= 0 or image_height <= 0:
                return None
            x = x / image_width * 100
            width = width / image_width * 100
            y = y / image_height * 100
            height = height / image_height * 100

        return {
            "x": self._clamp_percent(x),
            "y": self._clamp_percent(y),
            "width": self._clamp_percent(width),
            "height": self._clamp_percent(height),
        }

    def _json_script(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")

    def _text(self, value: Any) -> str:
        return escape(str(value), quote=True)

    def _number(self, value: Any) -> int | float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0
        if numeric.is_integer():
            return int(numeric)
        return round(numeric, 2)

    def _severity(self, value: Any) -> str:
        severity = str(value).lower()
        return severity if severity in _SEVERITY_STYLES else "low"

    def _clamp_percent(self, value: float) -> float:
        return round(max(0.0, min(100.0, value)), 2)

    def _format_percent(self, value: float) -> str:
        rounded = round(value, 2)
        if rounded.is_integer():
            return str(int(rounded))
        return str(rounded)
