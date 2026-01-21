// frontend/lifeops-ui/src/App.jsx
import { useEffect, useState } from "react";
import { createMission, runReflection, getLatestReflection, healthCheck } from "./api";



import ReflectionScreen from "./screens/ReflectionScreen";

export default function App() {
  const [backendOk, setBackendOk] = useState(true);
  const [missionReady, setMissionReady] = useState(false);
  const [reflectionData, setReflectionData] = useState(null);
  const [loading, setLoading] = useState(false);

  // -----------------------------
  // Health check on load
  // -----------------------------
  useEffect(() => {
    healthCheck()
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  }, []);

  // -----------------------------
  // Load last reflection (if exists)
  // -----------------------------
  useEffect(() => {
    getLatestReflection()
      .then((res) => {
        if (res?.last_reflection && res?.last_adaptation) {
          setReflectionData({
            reflection: res.last_reflection,
            adaptation: res.last_adaptation
          });
          setMissionReady(true);
        }
      })
      .catch(() => {});
  }, []);

  // -----------------------------
  // Demo mission (hackathon)
  // -----------------------------
  const startDemoMission = async () => {
    setLoading(true);
    try {
      await createMission({
        goal: "Build a production-ready Gemini 3 hackathon project",
        days: 7,
        hours_per_day: 3,
        skills: ["React", "Python", "FastAPI"],
        constraints: ["Limited daily time", "Learning while building"]
      });
      setMissionReady(true);
    } catch (e) {
      console.error(e);
      alert("Failed to create mission");
    }
    setLoading(false);
  };

  // -----------------------------
  // Run reflection
  // -----------------------------
  const handleReflection = async () => {
    setLoading(true);
    try {
      const res = await runReflection(25);
      setReflectionData(res);
    } catch (e) {
      console.error(e);
      alert("Reflection failed");
    }
    setLoading(false);
  };

  // -----------------------------
  // UI
  // -----------------------------
  if (!backendOk) {
    return (
      <div style={{ padding: 40 }}>
        <h2>❌ Backend not reachable</h2>
        <p>Make sure FastAPI is running on port 8000.</p>
      </div>
    );
  }

  if (!missionReady) {
    return (
      <div style={{ padding: 40 }}>
        <h1>🚀 LifeOps AI</h1>
        <p>An autonomous Gemini-powered mission agent.</p>
        <button onClick={startDemoMission} disabled={loading}>
          {loading ? "Initializing..." : "Start Demo Mission"}
        </button>
      </div>
    );
  }

  return (
    <div>
      <header style={{ padding: 20, borderBottom: "1px solid #ddd" }}>
        <h1>🧠 LifeOps AI</h1>
        <p>Reflection & Adaptation Dashboard</p>
        <button onClick={handleReflection} disabled={loading}>
          {loading ? "AI Thinking..." : "Run Reflection"}
        </button>
      </header>

      <main style={{ padding: 20 }}>
        {reflectionData ? (
          <ReflectionScreen
            reflection={reflectionData.reflection}
            adaptation={reflectionData.adaptation}
          />
        ) : (
          <p>No reflection data yet. Run reflection to begin.</p>
        )}
      </main>
    </div>
  );
}
