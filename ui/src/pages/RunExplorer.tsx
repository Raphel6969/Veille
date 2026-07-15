import { useEffect, useState } from "react";
import * as api from "../api";

export default function RunExplorer() {
  const [runList, setRunList] = useState<api.RunView[]>([]);
  const [selected, setSelected] = useState<api.RunView | null>(null);
  const [baseline, setBaseline] = useState<api.RunView | null>(null);

  useEffect(() => {
    api.runs().then(setRunList).catch(() => {});
  }, []);

  const view = (runId: string) => {
    api.runDetail(runId).then(setSelected).catch(() => {
      const found = runList.find((r) => r.run_id === runId);
      setSelected(found || null);
    });
  };

  return (
    <div>
      <h2>Run Explorer</h2>
      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ width: 300 }}>
          <h3>Saved Runs</h3>
          {runList.length === 0 && <p>No runs yet.</p>}
          {runList.map((r) => (
            <div
              key={r.run_id}
              onClick={() => { view(r.run_id); setBaseline(baseline ? null : r); }}
              style={{
                cursor: "pointer",
                padding: 4,
                background: selected?.run_id === r.run_id ? "#e0e0e0" : undefined,
              }}
            >
              {r.run_id.substring(0, 8)} — {r.task_id}
            </div>
          ))}
        </div>
        <div style={{ flex: 1 }}>
          <h3>{baseline && selected ? "Baseline vs selected" : "Detail"}</h3>
          {baseline && selected && <div style={{ background: "#fff", border: "1px solid #e8e7e3", borderRadius: 12, padding: 16, marginBottom: 12 }}>
            <p style={{ color: "#667085" }}>Comparison uses the same normalized run summaries shown by VEILLE.</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              <b>Metric</b><b>Baseline</b><b>Selected</b>
              {[["Cost", "total_cost_usd"], ["Latency", "total_latency_s"], ["Tool calls", "tool_calls"], ["Validation", "validation_checks"]].map(([label, key]) => <><span key={`${key}-label`}>{label}</span><span key={`${key}-base`}>{String(baseline.summary[key])}</span><span key={`${key}-selected`}>{String(selected.summary[key])}</span></>)}
            </div>
          </div>}
          {selected && (
            <pre style={{ fontSize: 12 }}>{JSON.stringify(selected, null, 2)}</pre>
          )}
        </div>
      </div>
    </div>
  );
}
