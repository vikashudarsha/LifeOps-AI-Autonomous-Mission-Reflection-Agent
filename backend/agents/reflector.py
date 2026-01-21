# backend/agents/reflector.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from gemini.client import get_client, GeminiClientError
from prompts.prompts import REFLECTION_PROMPT, ADAPTATION_PROMPT


def _validate_reflection_schema(reflection: Dict[str, Any]) -> None:
    if not isinstance(reflection, dict):
        raise ValueError("reflection must be a dict")
    for k in ["patterns", "root_causes", "planning_mistakes", "behavior_trends", "confidence_level"]:
        if k not in reflection:
            raise ValueError(f"reflection missing key: {k}")
    if reflection["confidence_level"] not in ["low", "medium", "high"]:
        raise ValueError("reflection.confidence_level must be low|medium|high")


def _validate_adaptation_schema(adaptation: Dict[str, Any]) -> None:
    if not isinstance(adaptation, dict):
        raise ValueError("adaptation must be a dict")
    for k in ["changes", "updated_strategy_summary", "updated_plan"]:
        if k not in adaptation:
            raise ValueError(f"adaptation missing key: {k}")
    if not isinstance(adaptation["changes"], list):
        raise ValueError("adaptation.changes must be a list")
    if not isinstance(adaptation["updated_plan"], dict):
        raise ValueError("adaptation.updated_plan must be a dict")
    if "phases" not in adaptation["updated_plan"] or not isinstance(adaptation["updated_plan"]["phases"], list):
        raise ValueError("adaptation.updated_plan.phases must be a list")


def _compact_history(history: List[Dict[str, Any]], max_entries: int = 50) -> List[Dict[str, Any]]:
    """
    Reduce noise and token usage while preserving what matters:
    - date
    - task_id
    - status
    - planned/actual
    - delays
    - feedback/energy
    """
    compact: List[Dict[str, Any]] = []
    sliced = history[-max_entries:] if len(history) > max_entries else history

    for day_entry in sliced:
        date = day_entry.get("date")
        logs = day_entry.get("logs", [])
        compact_logs = []
        for log in logs:
            compact_logs.append(
                {
                    "task_id": log.get("task_id"),
                    "status": log.get("status"),
                    "planned_minutes": log.get("planned_minutes"),
                    "actual_minutes": log.get("actual_minutes"),
                    "start_delay_minutes": log.get("start_delay_minutes"),
                    "user_feedback": log.get("user_feedback"),
                    "energy_level": log.get("energy_level"),
                }
            )
        compact.append({"date": date, "logs": compact_logs})

    return compact


def _fallback_reflection(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Very simple fallback so UI always works
    missed = 0
    completed = 0
    for d in history:
        for l in d.get("logs", []):
            if l.get("status") == "completed":
                completed += 1
            elif l.get("status") in ["missed", "deferred", "partial"]:
                missed += 1

    patterns = []
    if missed > completed:
        patterns.append("More tasks missed than completed in the recent window.")
    else:
        patterns.append("Completion rate is stable, but improvements are possible.")

    return {
        "patterns": patterns,
        "root_causes": ["Insufficient data from model; using basic heuristics."],
        "planning_mistakes": ["Estimates may be unrealistic for available time."],
        "behavior_trends": ["Inconsistent execution across days."],
        "confidence_level": "low",
    }


def _fallback_adaptation(original_plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "changes": [],
        "updated_strategy_summary": "No plan changes applied (fallback mode).",
        "updated_plan": {
            "phases": original_plan.get("phases", []),
        },
    }


def _merge_updated_plan(original_plan: Dict[str, Any], adaptation: Dict[str, Any], mission: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure the returned updated_plan is a full plan object the rest of the app expects.
    We keep the mission block and failure_risks if present, but replace phases with updated phases.
    """
    updated_plan: Dict[str, Any] = dict(original_plan) if isinstance(original_plan, dict) else {}

    # Replace phases with the adapted phases
    updated_phases = adaptation.get("updated_plan", {}).get("phases", [])
    updated_plan["phases"] = updated_phases

    # Keep/ensure mission block exists
    updated_plan.setdefault(
        "mission",
        {
            "goal": mission.get("goal", ""),
            "days": mission.get("days", 30),
            "hours_per_day": mission.get("hours_per_day", 2),
        },
    )

    # Ensure failure_risks exists (optional)
    updated_plan.setdefault("failure_risks", original_plan.get("failure_risks", []))
    updated_plan.setdefault("plan_assumptions", original_plan.get("plan_assumptions", []))

    return updated_plan


def reflect_and_adapt(
    *,
    mission: Dict[str, Any],
    original_plan: Dict[str, Any],
    history: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Runs:
      1) Reflection (patterns + root causes)
      2) Adaptation (changes + updated plan phases)

    Returns:
      (reflection_dict, adaptation_dict, updated_plan_full_dict)
    """
    if not isinstance(mission, dict) or not mission.get("goal"):
        raise ValueError("mission must be a dict with a 'goal' field.")
    if not isinstance(original_plan, dict) or "phases" not in original_plan:
        raise ValueError("original_plan must be a dict with 'phases'.")
    if not isinstance(history, list) or len(history) == 0:
        raise ValueError("history must be a non-empty list.")

    client = get_client()

    # Compact history to reduce token usage and improve quality
    compact_hist = _compact_history(history, max_entries=60)

    # Build context for the model (keep it concise)
    mission_context = {
        "goal": mission.get("goal"),
        "days": mission.get("days"),
        "hours_per_day": mission.get("hours_per_day"),
        "skills": mission.get("skills", []),
        "constraints": mission.get("constraints", []),
    }

    # -----------------
    # 1) Reflection
    # -----------------
    reflection_prompt = (
        REFLECTION_PROMPT
        + "\n\nInputs:\n"
        + json.dumps(
            {
                "mission": mission_context,
                "execution_history": compact_hist,
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    try:
        reflection = client.generate_json(reflection_prompt)
        _validate_reflection_schema(reflection)
    except (GeminiClientError, ValueError, json.JSONDecodeError):
        reflection = _fallback_reflection(compact_hist)

    # -----------------
    # 2) Adaptation
    # -----------------
    adaptation_prompt = (
        ADAPTATION_PROMPT
        + "\n\nInputs:\n"
        + json.dumps(
            {
                "mission": mission_context,
                "reflection": reflection,
                "original_plan": original_plan,
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    try:
        adaptation = client.generate_json(adaptation_prompt)
        _validate_adaptation_schema(adaptation)
    except (GeminiClientError, ValueError, json.JSONDecodeError):
        adaptation = _fallback_adaptation(original_plan)

    updated_plan = _merge_updated_plan(original_plan, adaptation, mission)

    return reflection, adaptation, updated_plan
