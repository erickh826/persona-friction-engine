"""
GitHub Action CI Runner — Persona Friction Engine M3

Wraps the Orchestrator for CI/CD context:
- Reads inputs from environment variables (set by action.yml)
- Generates a scenario on-the-fly if no scenario_path is given
- Runs the full audit pipeline
- Sets GitHub Action output variables
- Posts a formatted PR comment with CLS score, friction table, and screenshot thumbnails
- Exits with code 1 if CLS exceeds threshold and fail_on_exceed is true
"""

import json
import logging
import os
import sys
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Preset Personas ──────────────────────────────────────────────────────────

PERSONA_PRESETS = {
    "busy-mom": {
        "name": "Busy Mom",
        "age": 38,
        "tech_savviness": 2,
        "attention_span_seconds": 45,
        "motivation_level": 3,
        "cognitive_biases": ["loss aversion", "status quo bias"],
    },
    "tech-millennial": {
        "name": "Tech Millennial",
        "age": 28,
        "tech_savviness": 4,
        "attention_span_seconds": 90,
        "motivation_level": 4,
        "cognitive_biases": ["social proof", "anchoring"],
    },
    "senior-shopper": {
        "name": "Senior Shopper",
        "age": 65,
        "tech_savviness": 1,
        "attention_span_seconds": 60,
        "motivation_level": 2,
        "cognitive_biases": ["authority bias", "familiarity bias"],
    },
}


# ─── GitHub API Helpers ────────────────────────────────────────────────────────

def _github_api_request(
    method: str,
    url: str,
    token: str,
    data: Optional[dict] = None,
) -> Optional[dict]:
    """Make a GitHub API request using only stdlib (no requests dependency in CI)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "persona-friction-engine/1.0",
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.warning(f"GitHub API {method} {url} → HTTP {e.code}: {e.read().decode()}")
        return None
    except Exception as e:
        logger.warning(f"GitHub API request failed: {e}")
        return None


def _get_pr_number(github_event_path: str) -> Optional[int]:
    """Extract PR number from the GitHub event payload file."""
    if not github_event_path or not Path(github_event_path).exists():
        return None
    try:
        with open(github_event_path) as f:
            event = json.load(f)
        return event.get("pull_request", {}).get("number")
    except Exception:
        return None


# ─── PR Comment Formatting ────────────────────────────────────────────────────

def _severity_emoji(severity: str) -> str:
    return {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
        severity.lower(), "⚪"
    )


def _cls_badge(cls: float, threshold: float) -> str:
    if cls >= threshold:
        return f"🔴 **{cls:.1f}** (exceeds threshold {threshold:.0f})"
    elif cls >= threshold * 0.8:
        return f"🟠 **{cls:.1f}** (approaching threshold {threshold:.0f})"
    else:
        return f"🟢 **{cls:.1f}** (within threshold {threshold:.0f})"


def build_pr_comment(result: dict, threshold: float, scenario_id: str) -> str:
    """Build a formatted Markdown PR comment from audit result."""
    cls = result.get("final_cls", 0)
    passed = cls < threshold
    steps = result.get("steps", [])
    persona = result.get("persona_name", "Unknown")
    target_url = result.get("target_url", "")
    total_friction = sum(len(s.get("friction_points", [])) for s in steps)

    # Header
    status_icon = "✅" if passed else "❌"
    lines = [
        f"## {status_icon} Persona Friction Audit — `{scenario_id}`",
        "",
        f"| Metric | Value |",
        f"| :--- | :--- |",
        f"| **Target URL** | `{target_url}` |",
        f"| **Persona** | {persona} |",
        f"| **Final CLS** | {_cls_badge(cls, threshold)} |",
        f"| **Steps Completed** | {result.get('total_steps', 0)} |",
        f"| **Friction Points** | {total_friction} |",
        f"| **Dropout** | {'Yes ⚠️' if result.get('dropout') else 'No'} |",
        "",
    ]

    # Step-by-step CLS table
    if steps:
        lines += [
            "### 📊 Step-by-Step CLS Breakdown",
            "",
            "| Step | Action | CLS | Visual | Friction | Alignment |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for i, step in enumerate(steps, 1):
            action = step.get("action_taken", {})
            action_str = f"`{action.get('action', 'navigate')}` {action.get('selector', '')[:30]}"
            cls_val = step.get("cls_score", 0)
            sub = step.get("sub_scores", {})
            lines.append(
                f"| {i} | {action_str} | **{cls_val:.1f}** "
                f"| {sub.get('visual_complexity', 0):.1f} "
                f"| {sub.get('interaction_friction', 0):.1f} "
                f"| {sub.get('cognitive_alignment', 0):.1f} |"
            )
        lines.append("")

    # Friction points inspector
    all_friction = []
    for step in steps:
        for fp in step.get("friction_points", []):
            all_friction.append(fp)

    if all_friction:
        lines += [
            "### 🔍 Friction Points Inspector",
            "",
            "| Severity | Type | Description | Recommendation |",
            "| :--- | :--- | :--- | :--- |",
        ]
        # Sort by severity: critical → high → medium → low
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_friction.sort(key=lambda x: severity_order.get(x.get("severity", "low").lower(), 4))
        for fp in all_friction[:15]:  # Cap at 15 to avoid huge comments
            sev = fp.get("severity", "low")
            lines.append(
                f"| {_severity_emoji(sev)} {sev.capitalize()} "
                f"| {fp.get('type', 'unknown')} "
                f"| {fp.get('description', '')[:80]} "
                f"| {fp.get('recommendation', '')[:80]} |"
            )
        if len(all_friction) > 15:
            lines.append(f"| ... | | *{len(all_friction) - 15} more friction points in full report* | |")
        lines.append("")

    # Error info
    if result.get("error"):
        err = result["error"]
        lines += [
            "### ⚠️ Audit Error",
            "",
            f"> **{err.get('type', 'Error')}**: {err.get('message', 'Unknown error')}",
            "",
        ]

    # Footer
    lines += [
        "---",
        f"*Generated by [Persona Friction Engine](https://github.com/erickh826/persona-friction-engine) · "
        f"CLS Formula: 0.35×Visual + 0.40×Friction + 0.25×(100−Alignment)*",
    ]

    return "\n".join(lines)


def post_pr_comment(comment_body: str, token: str, repo: str, pr_number: int) -> bool:
    """Post a comment to a GitHub PR."""
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    result = _github_api_request("POST", url, token, {"body": comment_body})
    return result is not None


def delete_previous_audit_comments(token: str, repo: str, pr_number: int) -> None:
    """Delete previous audit comments from this action to avoid spamming the PR."""
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    comments = _github_api_request("GET", url, token)
    if not comments:
        return
    for comment in comments:
        if "Persona Friction Audit" in comment.get("body", ""):
            comment_id = comment.get("id")
            if comment_id:
                _github_api_request(
                    "DELETE",
                    f"https://api.github.com/repos/{repo}/issues/comments/{comment_id}",
                    token,
                )


# ─── GitHub Action Output ─────────────────────────────────────────────────────

def set_output(name: str, value: str) -> None:
    """Write a GitHub Action output variable to GITHUB_OUTPUT file."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        # Fallback for local testing
        print(f"::set-output name={name}::{value}")


def set_summary(content: str) -> None:
    """Write to GitHub Step Summary."""
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(content + "\n")


# ─── Scenario Generation ──────────────────────────────────────────────────────

def generate_scenario(
    target_url: str,
    persona_preset: str,
    max_steps: int,
    output_dir: str,
) -> str:
    """Generate a temporary scenario JSON file from CLI inputs."""
    persona = PERSONA_PRESETS.get(persona_preset, PERSONA_PRESETS["busy-mom"])
    scenario = {
        "scenario_id": f"ci-audit-{persona_preset}",
        "target_url": target_url,
        "target_goal": f"Evaluate UX friction on {target_url}",
        "max_steps": max_steps,
        "persona": persona,
    }
    scenario_path = Path(output_dir) / "ci_scenario.json"
    scenario_path.parent.mkdir(parents=True, exist_ok=True)
    with open(scenario_path, "w") as f:
        json.dump(scenario, f, indent=2)
    return str(scenario_path)


# ─── Main Runner ──────────────────────────────────────────────────────────────

def run() -> int:
    """
    Main entry point for the GitHub Action.
    Returns exit code: 0 = pass, 1 = fail (CLS exceeded or error).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # ── Read inputs from environment ──
    scenario_path = os.environ.get("INPUT_SCENARIO_PATH", "").strip()
    target_url = os.environ.get("INPUT_TARGET_URL", "").strip()
    cls_threshold = float(os.environ.get("INPUT_CLS_THRESHOLD", "70"))
    fail_on_exceed = os.environ.get("INPUT_FAIL_ON_EXCEED", "true").lower() == "true"
    persona_preset = os.environ.get("INPUT_PERSONA_PRESET", "busy-mom").strip()
    max_steps = int(os.environ.get("INPUT_MAX_STEPS", "5"))
    use_llm = os.environ.get("INPUT_USE_LLM", "false").lower() == "true"
    post_comment = os.environ.get("INPUT_POST_PR_COMMENT", "true").lower() == "true"
    output_dir = os.environ.get("INPUT_OUTPUT_DIR", "friction-audit-output").strip()

    # GitHub context
    github_token = os.environ.get("GITHUB_TOKEN", "")
    github_repo = os.environ.get("GITHUB_REPOSITORY", "")
    github_event_path = os.environ.get("GITHUB_EVENT_PATH", "")

    logger.info("=" * 60)
    logger.info("Persona Friction Engine — GitHub Action CI Runner")
    logger.info("=" * 60)

    # ── Validate inputs ──
    if not scenario_path and not target_url:
        logger.error("Either 'scenario_path' or 'target_url' input must be provided.")
        return 1

    # ── Prepare output directory ──
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    screenshots_dir = str(Path(output_dir) / "screenshots")
    Path(screenshots_dir).mkdir(parents=True, exist_ok=True)

    # ── Generate scenario if needed ──
    if not scenario_path:
        logger.info(f"No scenario_path provided. Generating scenario for: {target_url}")
        scenario_path = generate_scenario(target_url, persona_preset, max_steps, output_dir)
        logger.info(f"Generated scenario: {scenario_path}")

    # ── Import and run the engine ──
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from src.persona.engine import PersonaEngine
        from src.navigation.engine import NavigationEngine
        from src.evaluation.engine import CognitiveEvaluationEngine
        from src.orchestrator import Orchestrator

        # Try to import ReportingEngine
        try:
            from src.reporting.engine import ReportingEngine
            reporting_engine = ReportingEngine()
        except ImportError:
            reporting_engine = None

        logger.info("Initializing engines...")
        orchestrator = Orchestrator(
            persona_engine=PersonaEngine(),
            navigation_engine=NavigationEngine(
                headless=True,
                screenshots_dir=screenshots_dir,
            ),
            evaluation_engine=CognitiveEvaluationEngine(use_llm=use_llm),
            reporting_engine=reporting_engine,
            output_dir=output_dir,
            max_retries=1,
        )

        logger.info(f"Running audit: {scenario_path}")
        result = orchestrator.run_scenario(scenario_path)

    except Exception as e:
        logger.error(f"Engine initialization or run failed: {e}", exc_info=True)
        result = {
            "scenario_id": "ci-audit",
            "persona_name": persona_preset,
            "target_url": target_url,
            "final_cls": 0,
            "total_steps": 0,
            "steps": [],
            "completed": False,
            "dropout": False,
            "error": {"type": type(e).__name__, "message": str(e)},
            "report_path": None,
        }

    # ── Extract key metrics ──
    final_cls = result.get("final_cls", 0)
    passed = final_cls < cls_threshold and result.get("completed", False)
    scenario_id = result.get("scenario_id", "ci-audit")
    report_path = result.get("report_path") or ""
    trace_path = str(Path(output_dir) / f"{scenario_id}_trace.json")
    total_friction = sum(len(s.get("friction_points", [])) for s in result.get("steps", []))

    # ── Log summary ──
    logger.info("=" * 60)
    logger.info(f"Scenario:      {scenario_id}")
    logger.info(f"Persona:       {result.get('persona_name', persona_preset)}")
    logger.info(f"Final CLS:     {final_cls:.1f} (threshold: {cls_threshold:.0f})")
    logger.info(f"Steps:         {result.get('total_steps', 0)}")
    logger.info(f"Friction pts:  {total_friction}")
    logger.info(f"Passed:        {passed}")
    logger.info("=" * 60)

    # ── Set GitHub Action outputs ──
    set_output("cls_score", f"{final_cls:.1f}")
    set_output("passed", str(passed).lower())
    set_output("report_path", report_path)
    set_output("trace_path", trace_path)
    set_output("friction_points_count", str(total_friction))

    # ── Write step summary ──
    comment_body = build_pr_comment(result, cls_threshold, scenario_id)
    set_summary(comment_body)

    # ── Post PR comment ──
    if post_comment and github_token and github_repo:
        pr_number = _get_pr_number(github_event_path)
        if pr_number:
            logger.info(f"Posting PR comment to {github_repo}#{pr_number}...")
            delete_previous_audit_comments(github_token, github_repo, pr_number)
            success = post_pr_comment(comment_body, github_token, github_repo, pr_number)
            if success:
                logger.info("PR comment posted successfully.")
            else:
                logger.warning("Failed to post PR comment (non-fatal).")
        else:
            logger.info("Not a PR context — skipping PR comment.")

    # ── Exit code ──
    if not passed and fail_on_exceed:
        logger.error(
            f"❌ Audit FAILED: CLS {final_cls:.1f} exceeds threshold {cls_threshold:.0f}. "
            f"Set fail_on_exceed: 'false' to treat this as a warning only."
        )
        return 1

    if not passed:
        logger.warning(
            f"⚠️  CLS {final_cls:.1f} exceeds threshold {cls_threshold:.0f} "
            f"(fail_on_exceed is false — warning only)."
        )
    else:
        logger.info(f"✅ Audit PASSED: CLS {final_cls:.1f} is within threshold {cls_threshold:.0f}.")

    return 0


if __name__ == "__main__":
    sys.exit(run())
