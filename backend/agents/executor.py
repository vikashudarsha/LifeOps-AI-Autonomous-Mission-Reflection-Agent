# backend/agents/executor.py
from __future__ import annotations

import json
from typing import Any, Dict, List

from gemini.client import get_client, GeminiClientError
from prompts.prompts import DAILY_EXECUTION_PROMPT


def _validate_daily_plan_schema(daily_plan: Dict[str, Any]) -> None:
    """
    Minimal validation to keep UI stable.
    """
    if not isinstance(daily_plan, dict):
        raise ValueError("daily_plan must be a dict.")

    required_keys = ["date", "total_hours_available", "prioritized_tasks", "completion_confidence"]
    for k in required_keys:
        if k not in daily_plan:
            raise ValueError(f"daily_plan missing required key: {k}")

    if not isinstance(daily_plan["prioritized_tasks"], list) or len(daily_plan["prioritized_tasks"]) == 0:
        raise ValueError("daily_plan.prioritized_tasks must be a non-empty list.")

    for t in daily_plan["prioritized_tasks"]:
        if not isinstance(t, dict):
            raise ValueError("Each prioritized task must be an object.")
        for tk in ["task_id", "steps", "estimated_hours", "definition_of_done"]:
            if tk not in t:
                raise ValueError(f"Each prioritized task missing: {tk}")
        if not isinstance(t["steps"], list) or len(t["steps"]) == 0:
            raise ValueError("Task steps must be a non-empty list.")


def _fallback_daily_plan(date: str, hours_available: float, selected_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Simple fallback plan if Gemini fails (keeps demo running).
    """
    tasks = []
    remaining = float(hours_available)

    for t in selected_tasks[:3]:
        est = float(t.get("effort_hours", 1))
        est = min(est, max(0.25, remaining))
        remaining -= est

        tasks.append(
            {
                "task_id": t.get("id", "T?"),
                "why_this_now": "Next pending task based on mission plan.",
                "steps": [
                    f"Start: {t.get('objective', 'Work on task')}",
                    "Work in 25-minute focus blocks",
                    "Write down what is done and what is blocked",
                    "Mark complete or note what remains",
                ],
                "estimated_hours": round(est, 2),
                "definition_of_done": t.get("success_criteria", "Task completed as defined in plan."),
            }
        )
        if remaining <= 0.25:
            break

    return {
        "date": date,
        "total_hours_available": hours_available,
        "prioritized_tasks": tasks,
        "time_budget": {
            "planned_total_hours": round(hours_available - max(0.0, remaining), 2),
            "buffer_hours": round(max(0.0, remaining), 2),
        },
        "completion_confidence": 60,
        "assumptions": ["Fallback plan used due to model/API issue."],
    }


def generate_daily_plan(
    *,
    date: str,
    hours_available: float,
    mission: Dict[str, Any],
    selected_tasks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Uses Gemini to create a focused daily execution plan.

    Args:
        date: "YYYY-MM-DD"
        hours_available: available hours today
        mission: mission dict stored in memory
        selected_tasks: list of task dicts (from master plan), each should include:
            - id
            - objective
            - effort_hours
            - depends_on
            - success_criteria

    Returns:
        dict daily plan (schema defined in DAILY_EXECUTION_PROMPT)
    """
    if not date or not isinstance(date, str):
        raise ValueError("date must be a non-empty string (YYYY-MM-DD).")

    if hours_available <= 0:
        raise ValueError("hours_available must be > 0.")

    if not isinstance(mission, dict) or not mission.get("goal"):
        raise ValueError("mission must be a dict with a 'goal' field.")

    if not isinstance(selected_tasks, list) or len(selected_tasks) == 0:
        raise ValueError("selected_tasks must be a non-empty list.")

    client = get_client()

    # Build a compact input so the model stays focused and returns clean JSON
    mission_context = {
        "goal": mission.get("goal"),
        "days": mission.get("days"),
        "hours_per_day": mission.get("hours_per_day"),
        "skills": mission.get("skills", []),
        "constraints": mission.get("constraints", []),
    }

    # Only pass key fields the model needs
    tasks_context = []
    for t in selected_tasks:
        tasks_context.append(
            {
                "id": t.get("id"),
                "objective": t.get("objective"),
                "effort_hours": t.get("effort_hours"),
                "depends_on": t.get("depends_on", []),
                "success_criteria": t.get("success_criteria"),
            }
        )

    prompt = (
        DAILY_EXECUTION_PROMPT
        + "\n\nToday's Inputs:\n"
        + json.dumps(
            {
                "date": date,
                "hours_available": hours_available,
                "mission": mission_context,
                "selected_tasks": tasks_context,
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    try:
        daily_plan = client.generate_json(prompt)
        _validate_daily_plan_schema(daily_plan)

        # Ensure numeric fields are sane
        daily_plan["total_hours_available"] = float(daily_plan["total_hours_available"])
        daily_plan["completion_confidence"] = int(daily_plan["completion_confidence"])

        # If time_budget missing, add it
        if "time_budget" not in daily_plan:
            planned = sum(float(t.get("estimated_hours", 0)) for t in daily_plan["prioritized_tasks"])
            daily_plan["time_budget"] = {
                "planned_total_hours": round(planned, 2),
                "buffer_hours": round(max(0.0, hours_available - planned), 2),
            }

        return daily_plan

    except (GeminiClientError, ValueError, KeyError, json.JSONDecodeError):
        # Keep hackathon demo robust even if model returns unexpected output
        return _fallback_daily_plan(date, hours_available, selected_tasks)
