# backend/agents/planner.py
from __future__ import annotations

import json
from typing import Any, Dict

from gemini.client import get_client, GeminiClientError
from prompts.prompts import MISSION_INTAKE_PROMPT, MASTER_PLANNER_PROMPT


def _validate_plan_schema(plan: Dict[str, Any]) -> None:
    """
    Minimal validation to keep the app stable and judge-friendly.
    Raises ValueError if the structure is not as expected.
    """
    if not isinstance(plan, dict):
        raise ValueError("Plan must be a dict.")

    if "phases" not in plan or not isinstance(plan["phases"], list) or len(plan["phases"]) == 0:
        raise ValueError("Plan must include a non-empty 'phases' list.")

    # Validate tasks exist and have IDs
    any_task = False
    for phase in plan["phases"]:
        tasks = phase.get("tasks", [])
        if isinstance(tasks, list) and len(tasks) > 0:
            any_task = True
            for t in tasks:
                if not isinstance(t, dict) or "id" not in t:
                    raise ValueError("Each task must be an object with an 'id' field.")
    if not any_task:
        raise ValueError("Plan must include at least one task.")


def create_plan(mission: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a mission plan using Gemini 3 via prompts/prompts.py templates.

    Args:
        mission: {
          "goal": str,
          "days": int,
          "hours_per_day": float,
          "skills": [str],
          "constraints": [str],
          ...
        }

    Returns:
        dict plan in the schema defined in MASTER_PLANNER_PROMPT.
    """
    if not isinstance(mission, dict) or not mission.get("goal"):
        raise ValueError("Mission must be a dict with a 'goal' field.")

    client = get_client()

    # 1) Mission intake (optional, but improves plan quality & judge-readability)
    intake_prompt = (
        MISSION_INTAKE_PROMPT
        + "\n\nMission Input:\n"
        + json.dumps(mission, indent=2, ensure_ascii=False)
    )

    try:
        intake = client.generate_json(intake_prompt)
    except GeminiClientError:
        # Intake failure should not block planning; continue with mission only.
        intake = {
            "mission_summary": f"{mission.get('goal')}",
            "assumptions": [],
            "success_factors": [],
            "risks": [],
        }

    # 2) Master plan prompt
    master_prompt = (
        MASTER_PLANNER_PROMPT
        + "\n\nMission Input:\n"
        + json.dumps(mission, indent=2, ensure_ascii=False)
        + "\n\nMission Intake Summary:\n"
        + json.dumps(intake, indent=2, ensure_ascii=False)
    )

    plan = client.generate_json(master_prompt)

    # 3) Minimal validation + small cleanup
    _validate_plan_schema(plan)

    # Ensure mission block exists for consistency (some models may omit it)
    plan.setdefault("mission", {
        "goal": mission.get("goal", ""),
        "days": mission.get("days", 30),
        "hours_per_day": mission.get("hours_per_day", 2),
    })

    return plan
