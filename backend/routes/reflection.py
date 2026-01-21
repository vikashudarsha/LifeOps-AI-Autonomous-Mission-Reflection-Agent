# backend/routes/reflection.py
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.reflector import reflect_and_adapt

router = APIRouter(prefix="/reflection", tags=["Reflection"])

# ----------------------------
# Memory Helpers
# ----------------------------
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


# ----------------------------
# Request / Response Models
# ----------------------------
class ReflectRunRequest(BaseModel):
    window: int = Field(25, ge=1, le=300, description="How many recent history entries to analyze")


class ReflectRunResponse(BaseModel):
    reflection: Dict[str, Any]
    adaptation: Dict[str, Any]
    updated_plan: Dict[str, Any]


# ----------------------------
# Routes
# ----------------------------
@router.get("/latest")
def latest_reflection() -> Dict[str, Any]:
    """
    Return last saved reflection/adaptation (for UI refresh).
    """
    state = load_state()
    return {
        "last_reflection": state.get("last_reflection"),
        "last_adaptation": state.get("last_adaptation"),
        "last_updated": state.get("last_updated"),
    }


@router.post("/run", response_model=ReflectRunResponse)
def run_reflection(payload: ReflectRunRequest) -> ReflectRunResponse:
    """
    Run reflection + adaptation and update the master plan in state.json.
    """
    state = load_state()
    mission = state.get("mission")
    plan = state.get("plan")
    history = state.get("history", [])

    if not mission or not plan:
        raise HTTPException(status_code=400, detail="No mission/plan found. Create a mission first.")
    if not history:
        raise HTTPException(status_code=400, detail="No execution history found. Log tasks first.")

    recent_history = history[-payload.window:]

    try:
        reflection, adaptation, updated_plan = reflect_and_adapt(
            mission=mission,
            original_plan=plan,
            history=recent_history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reflector agent failed: {e}")

    # Save results
    state["plan"] = updated_plan
    state["last_reflection"] = reflection
    state["last_adaptation"] = adaptation

    save_state(state)

    return ReflectRunResponse(
        reflection=reflection,
        adaptation=adaptation,
        updated_plan=updated_plan,
    )
