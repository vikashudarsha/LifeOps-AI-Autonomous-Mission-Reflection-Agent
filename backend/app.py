# backend/app.py
"""
LifeOps AI Backend (FastAPI)
- Mission planning (Planner agent)
- Daily execution (Executor agent)
- Reflection & adaptation (Reflector agent)
- Simple persistent memory (memory/state.json)

Run:
  pip install -r requirements.txt
  uvicorn app:app --reload --port 8000
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Import your agents (you will implement these files) ---
# Each agent function should return Python dicts (not raw text).
from agents.planner import create_plan
from agents.executor import generate_daily_plan
from agents.reflector import reflect_and_adapt




# ----------------------------
# Paths & Memory Helpers
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent
MEMORY_PATH = BASE_DIR / "memory" / "state.json"


def _ensure_memory_file() -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MEMORY_PATH.exists():
        default_state = {
            "mission": None,
            "plan": None,
            "history": [],  # list of task execution logs
            "last_updated": None,
        }
        MEMORY_PATH.write_text(json.dumps(default_state, indent=2), encoding="utf-8")


def load_state() -> Dict[str, Any]:
    _ensure_memory_file()
    try:
        return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read memory/state.json: {e}")


def save_state(state: Dict[str, Any]) -> None:
    _ensure_memory_file()
    state["last_updated"] = datetime.utcnow().isoformat() + "Z"
    try:
        MEMORY_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write memory/state.json: {e}")


# ----------------------------
# Request/Response Models
# ----------------------------
class MissionCreateRequest(BaseModel):
    goal: str = Field(..., min_length=5, description="High-level mission goal")
    days: int = Field(30, ge=1, le=365, description="Mission duration in days")
    hours_per_day: float = Field(2.0, ge=0.25, le=24, description="Available time per day")
    skills: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)


class MissionCreateResponse(BaseModel):
    mission: Dict[str, Any]
    plan: Dict[str, Any]


class DailyPlanRequest(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    hours_available: float = Field(2.0, ge=0.25, le=24)
    # Optional: force today tasks by IDs; if omitted, backend selects next pending tasks
    task_ids: Optional[List[str]] = None


class DailyPlanResponse(BaseModel):
    date: str
    daily_plan: Dict[str, Any]


class TaskLog(BaseModel):
    task_id: str
    status: str = Field(..., description="completed|missed|deferred|partial")
    planned_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    start_delay_minutes: Optional[int] = None
    user_feedback: Optional[str] = None
    energy_level: Optional[str] = None
    timestamp: Optional[str] = None  # ISO time


class LogExecutionRequest(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    logs: List[TaskLog]



class ReflectRequest(BaseModel):
    # How many recent days/log entries to consider
    window: int = Field(25, ge=1, le=300)


class ReflectResponse(BaseModel):
    reflection: Dict[str, Any]
    adaptation: Dict[str, Any]
    updated_plan: Dict[str, Any]


# ----------------------------
# FastAPI App
# ----------------------------
app = FastAPI(
    title="LifeOps AI Backend",
    version="1.0.0",
    description="Gemini-powered long-running mission agent with planning, execution, reflection and adaptation.",
)

# CORS for React dev server (Vite default: 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Routers (AFTER app is created)
from routes.mission import router as mission_router
from routes.reflection import router as reflection_router

app.include_router(mission_router)
app.include_router(reflection_router)

# ----------------------------
# Utility: Pick next tasks (simple)
# ----------------------------
def _flatten_tasks(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = []
    for phase in plan.get("phases", []):
        for t in phase.get("tasks", []):
            tasks.append(t)
    return tasks


def _completed_task_ids(history: List[Dict[str, Any]]) -> set:
    done = set()
    for item in history:
        for log in item.get("logs", []):
            if log.get("status") == "completed":
                done.add(log.get("task_id"))
    return done


def _next_pending_tasks(plan: Dict[str, Any], history: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    all_tasks = _flatten_tasks(plan)
    done = _completed_task_ids(history)

    pending = [t for t in all_tasks if t.get("id") not in done]
    return pending[:limit]


# ----------------------------
# Routes
# ----------------------------
@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/state")
def get_state() -> Dict[str, Any]:
    """Debug-friendly endpoint (safe for dev)."""
    return load_state()


@app.post("/mission/create", response_model=MissionCreateResponse)
def mission_create(payload: MissionCreateRequest) -> MissionCreateResponse:
    """
    Create a new mission + master plan using Planner agent.
    Saves mission + plan into memory/state.json.
    """
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
        plan = create_plan(mission=mission)
        if not isinstance(plan, dict):
            raise ValueError("Planner agent must return a dict (parsed JSON).")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planner failed: {e}")

    state["mission"] = mission
    state["plan"] = plan
    state["history"] = []
    save_state(state)

    return MissionCreateResponse(mission=mission, plan=plan)


@app.post("/mission/daily-plan", response_model=DailyPlanResponse)
def mission_daily_plan(payload: DailyPlanRequest) -> DailyPlanResponse:
    """
    Generate today's execution plan using Executor agent.
    If task_ids not provided, the backend picks next pending tasks from master plan.
    """
    state = load_state()
    mission = state.get("mission")
    plan = state.get("plan")

    if not mission or not plan:
        raise HTTPException(status_code=400, detail="No mission found. Create a mission first.")

    # Select tasks
    if payload.task_ids:
        all_tasks = _flatten_tasks(plan)
        selected = [t for t in all_tasks if t.get("id") in set(payload.task_ids)]
    else:
        selected = _next_pending_tasks(plan=plan, history=state.get("history", []), limit=3)

    if not selected:
        raise HTTPException(status_code=200, detail="No pending tasks found. Mission may be complete.")

    try:
        daily_plan = generate_daily_plan(
            date=payload.date,
            hours_available=payload.hours_available,
            mission=mission,
            selected_tasks=selected,
        )
        if not isinstance(daily_plan, dict):
            raise ValueError("Executor agent must return a dict (parsed JSON).")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Executor failed: {e}")

    return DailyPlanResponse(date=payload.date, daily_plan=daily_plan)


@app.post("/mission/log", summary="Save execution logs")
def mission_log(payload: LogExecutionRequest) -> Dict[str, Any]:
    """
    Save user execution logs (completed/missed tasks) into memory.
    This history powers the Reflection & Adaptation screen.
    """
    state = load_state()
    if not state.get("mission") or not state.get("plan"):
        raise HTTPException(status_code=400, detail="No mission found. Create a mission first.")

    entry = {
        "date": payload.date,
        "logs": [l.model_dump() for l in payload.logs],
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }

    # Ensure timestamps exist
    for log in entry["logs"]:
        if not log.get("timestamp"):
            log["timestamp"] = datetime.utcnow().isoformat() + "Z"

    state.setdefault("history", []).append(entry)
    save_state(state)

    return {"ok": True, "saved": entry}


@app.post("/mission/reflect", response_model=ReflectResponse)
def mission_reflect(payload: ReflectRequest) -> ReflectResponse:
    """
    Run Reflection + Adaptation using Reflector agent.
    Updates the plan in memory/state.json.
    Returns reflection insights + adaptation changes + updated plan.
    """
    state = load_state()
    mission = state.get("mission")
    plan = state.get("plan")
    history = state.get("history", [])

    if not mission or not plan:
        raise HTTPException(status_code=400, detail="No mission found. Create a mission first.")
    if not history:
        raise HTTPException(status_code=400, detail="No history logs found. Log executions first.")

    # Take recent window logs (by entries, not days)
    recent = history[-payload.window:]

    try:
        reflection, adaptation, updated_plan = reflect_and_adapt(
            mission=mission,
            original_plan=plan,
            history=recent,
        )
        if not all(isinstance(x, dict) for x in [reflection, adaptation, updated_plan]):
            raise ValueError("Reflector must return (dict, dict, dict).")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reflector failed: {e}")

    # Persist updated plan
    state["plan"] = updated_plan
    # Store latest reflection/adaptation for UI convenience
    state["last_reflection"] = reflection
    state["last_adaptation"] = adaptation
    save_state(state)

    return ReflectResponse(
        reflection=reflection,
        adaptation=adaptation,
        updated_plan=updated_plan,
    )
