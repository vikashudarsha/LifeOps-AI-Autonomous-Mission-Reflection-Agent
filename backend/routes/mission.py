# backend/routes/mission.py
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.planner import create_plan
from agents.executor import generate_daily_plan
from agents.reflector import reflect_and_adapt

router = APIRouter(prefix="/mission", tags=["Mission"])

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
STATE_PATH = BASE_DIR / "memory" / "state.json"


def _ensure_state_file() -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        default_state = {
            "mission": None,
            "plan": None,
            "history": [],
            "last_reflection": None,
            "last_adaptation": None,
            "last_updated": None,
        }
        STATE_PATH.write_text(json.dumps(default_state, indent=2), encoding="utf-8")


def load_state() -> Dict[str, Any]:
    _ensure_state_file()
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read state.json: {e}")


def save_state(state: Dict[str, Any]) -> None:
    _ensure_state_file()
    state["last_updated"] = datetime.utcnow().isoformat() + "Z"
    try:
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write state.json: {e}")


class MissionCreateRequest(BaseModel):
    goal: str = Field(..., min_length=5)
    days: int = Field(30, ge=1, le=365)
    hours_per_day: float = Field(2.0, ge=0.25, le=24)
    skills: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)


class DailyPlanRequest(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    hours_available: float = Field(2.0, ge=0.25, le=24)
    task_ids: Optional[List[str]] = None


class TaskLog(BaseModel):
    task_id: str
    status: str
    planned_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    start_delay_minutes: Optional[int] = None
    user_feedback: Optional[str] = None
    energy_level: Optional[str] = None


class LogExecutionRequest(BaseModel):
    date: str
    logs: List[TaskLog]


class ReflectRequest(BaseModel):
    window: int = Field(25, ge=1, le=300)


@router.post("/create")
def create_mission(payload: MissionCreateRequest):
    state = load_state()

    mission = {
        "goal": payload.goal.strip(),
        "days": payload.days,
        "hours_per_day": payload.hours_per_day,
        "skills": payload.skills,
        "constraints": payload.constraints,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    try:
        plan = create_plan(mission)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planner failed: {e}")

    state["mission"] = mission
    state["plan"] = plan
    state["history"] = []
    state["last_reflection"] = None
    state["last_adaptation"] = None

    save_state(state)
    return {"mission": mission, "plan": plan}


@router.post("/daily-plan")
def daily_plan(payload: DailyPlanRequest):
    state = load_state()
    mission = state.get("mission")
    plan = state.get("plan")

    if not mission or not plan:
        raise HTTPException(status_code=400, detail="Mission not initialized")

    tasks: List[Dict[str, Any]] = []
    for phase in plan.get("phases", []):
        tasks.extend(phase.get("tasks", []))

    if payload.task_ids:
        wanted = set(payload.task_ids)
        selected_tasks = [t for t in tasks if t.get("id") in wanted]
    else:
        selected_tasks = tasks[:3]

    if not selected_tasks:
        raise HTTPException(status_code=400, detail="No tasks available to plan today.")

    try:
        result = generate_daily_plan(
            date=payload.date,
            hours_available=payload.hours_available,
            mission=mission,
            selected_tasks=selected_tasks,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Executor failed: {e}")

    return result


@router.post("/log")
def log_execution(payload: LogExecutionRequest):
    state = load_state()

    if not state.get("mission"):
        raise HTTPException(status_code=400, detail="Mission not initialized")

    entry = {
        "date": payload.date,
        "logs": [log.model_dump() for log in payload.logs],
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }

    state.setdefault("history", []).append(entry)
    save_state(state)

    return {"status": "saved", "entry": entry}


@router.post("/reflect")
def reflect(payload: ReflectRequest):
    state = load_state()

    mission = state.get("mission")
    plan = state.get("plan")
    history = state.get("history", [])

    if not mission or not plan:
        raise HTTPException(status_code=400, detail="Mission not initialized")
    if not history:
        raise HTTPException(status_code=400, detail="No execution history available")

    recent_history = history[-payload.window :]

    try:
        reflection, adaptation, updated_plan = reflect_and_adapt(
            mission=mission,
            original_plan=plan,
            history=recent_history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reflection failed: {e}")

    state["plan"] = updated_plan
    state["last_reflection"] = reflection
    state["last_adaptation"] = adaptation
    save_state(state)

    return {
        "reflection": reflection,
        "adaptation": adaptation,
        "updated_plan": updated_plan,
    }
