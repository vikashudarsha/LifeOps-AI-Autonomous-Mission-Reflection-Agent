// frontend/lifeops-ui-new/src/api.js

const API_BASE = "http://127.0.0.1:8000";

/* -----------------------------
   Mission APIs
----------------------------- */

export async function createMission(payload) {
  const res = await fetch(`${API_BASE}/mission/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!res.ok) throw new Error("Failed to create mission");
  return res.json();
}

export async function getDailyPlan(payload) {
  const res = await fetch(`${API_BASE}/mission/daily-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!res.ok) throw new Error("Failed to generate daily plan");
  return res.json();
}

export async function logExecution(payload) {
  const res = await fetch(`${API_BASE}/mission/log`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!res.ok) throw new Error("Failed to save execution log");
  return res.json();
}

/* -----------------------------
   Reflection (🔥 Winning Moment)
----------------------------- */

export async function runReflection(window = 25) {
  const res = await fetch(`${API_BASE}/mission/reflect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ window })
  });

  if (!res.ok) throw new Error("Reflection failed");
  return res.json();
}

export async function getLatestReflection() {
  const res = await fetch(`${API_BASE}/state`);
  if (!res.ok) throw new Error("Failed to fetch state");
  return res.json();
}


/* -----------------------------
   Utility
----------------------------- */

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}
