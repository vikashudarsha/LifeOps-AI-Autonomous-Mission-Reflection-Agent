// frontend/lifeops-ui/src/screens/ReflectionScreen.jsx
import { useEffect, useState } from "react";
import { runReflection } from "../api";

export default function ReflectionScreen() {
  const [reflection, setReflection] = useState(null);
  const [adaptation, setAdaptation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchReflection() {
      try {
        setLoading(true);
        const data = await runReflection(25);
        setReflection(data.reflection);
        setAdaptation(data.adaptation);
      } catch (err) {
        setError("Failed to load reflection data");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchReflection();
  }, []);

  if (loading) {
    return <p className="muted">🧠 AI is reflecting on your progress...</p>;
  }

  if (error) {
    return <p className="error">{error}</p>;
  }

  if (!reflection || !adaptation) {
    return null;
  }

  return (
    <div className="reflection-container">
      {/* Reflection Summary */}
      <section className="card">
        <h2>🧠 Reflection Summary</h2>
        <p className="muted">
          Confidence Level: <strong>{reflection.confidence_level}</strong>
        </p>

        <h3>Detected Patterns</h3>
        <ul>
          {reflection.patterns?.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      </section>

      {/* Root Causes */}
      <section className="card">
        <h2>⚠️ Root Causes</h2>
        <ul>
          {reflection.root_causes?.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      </section>

      {/* Planning Mistakes */}
      {reflection.planning_mistakes?.length > 0 && (
        <section className="card">
          <h2>❌ Planning Mistakes</h2>
          <ul>
            {reflection.planning_mistakes.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Behavior Trends */}
      {reflection.behavior_trends?.length > 0 && (
        <section className="card">
          <h2>📈 Behavior Trends</h2>
          <ul>
            {reflection.behavior_trends.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Adaptation */}
      <section className="card">
        <h2>🔁 Plan Adaptation</h2>

        {adaptation.changes?.length === 0 && (
          <p className="muted">No structural changes were required.</p>
        )}

        {adaptation.changes?.map((change, idx) => (
          <div key={idx} className="change-block">
            <p>
              <strong>❌ Before:</strong> {change.before}
            </p>
            <p>
              <strong>✅ After:</strong> {change.after}
            </p>
            <p className="reason">💡 Reason: {change.reason}</p>
          </div>
        ))}
      </section>

      {/* Updated Strategy */}
      <section className="card card-highlight">
        <h2>🧭 Updated Strategy</h2>
        <p>{adaptation.updated_strategy_summary}</p>
      </section>
    </div>
  );
}
