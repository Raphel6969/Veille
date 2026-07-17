import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import * as api from "../api";

type TimelineEvent = {
  timestamp?: string | null;
  event_type?: string;
  tool_name?: string | null;
  model_name?: string | null;
  status?: string | null;
  duration_ms?: number | null;
  cost_usd?: number | null;
};

function value(summary: Record<string, unknown>, key: string): string {
  const item = summary[key];
  if (typeof item === "number") return key.includes("cost") ? `$${item.toFixed(4)}` : String(item);
  if (typeof item === "boolean") return item ? "Yes" : "No";
  return item == null ? "—" : String(item);
}

export default function RunExplorer() {
  const [runList, setRunList] = useState<api.RunView[]>([]);
  const [selected, setSelected] = useState<api.RunView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [params] = useSearchParams();

  const view = async (runId: string) => {
    setError(null);
    try {
      setSelected(await api.runDetail(runId));
    } catch (loadError: unknown) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load this run.");
    }
  };

  useEffect(() => { api.runs().then(setRunList).catch(() => setError("Unable to load saved runs.")); }, []);
  useEffect(() => {
    const runId = params.get("selected");
    if (runId) void view(runId);
  }, [params]);

  const summary = selected?.summary ?? {};
  const timeline = (selected?.timeline ?? []) as TimelineEvent[];
  const policy = selected?.policy as { policy_events?: unknown[]; intervention_events?: unknown[] } | undefined;
  const cache = selected?.cache ?? {};
  const validation = selected?.validation ?? {};

  return (
    <div>
      <h2>Run Explorer</h2>
      <p className="text-subtle">Select a saved run to inspect the operational evidence Veille captured.</p>
      <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
        <aside className="glass-panel" style={{ width: 330, padding: 16 }}>
          <h3>Saved Runs</h3>
          {runList.length === 0 && <p className="text-subtle">No runs yet. Run a workflow first.</p>}
          {runList.map((run) => (
            <button
              key={run.run_id}
              onClick={() => void view(run.run_id)}
              className={selected?.run_id === run.run_id ? "glass-button active" : "glass-button"}
              style={{ display: "block", width: "100%", margin: "8px 0" }}
            >
              <strong>{run.run_id.substring(0, 8)}</strong><br />
              <span className="text-subtle" style={{ fontSize: "12px", color: selected?.run_id === run.run_id ? "var(--text-accent)" : "var(--text-secondary)" }}>{run.task_id}</span>
            </button>
          ))}
        </aside>
        <section style={{ flex: 1, minWidth: 0 }}>
          <h3>Evidence</h3>
          {error && <p style={{ color: "#ef4444" }}>{error}</p>}
          {!selected && !error && <p className="text-subtle">Select a run on the left. Its cost, policy, validation, cache, and event timeline will appear here.</p>}
          {selected && <>
            <p><strong>Run:</strong> {selected.run_id} &nbsp; <strong>Task:</strong> {selected.task_id}</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(140px, 1fr))", gap: 12 }}>
              {["total_cost_usd", "total_latency_s", "tool_calls", "cache_served", "semantic_duplicates", "estimated_savings_usd"].map((key) => (
                <div key={key} className="glass-card">
                  <small className="text-subtle">{key.replace(/_/g, " ")}</small><br /><strong>{value(summary, key)}</strong>
                </div>
              ))}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 12 }}>
              <div className="glass-card"><strong>Policy events</strong><br />{policy?.policy_events?.length ?? 0}</div>
              <div className="glass-card"><strong>Cache reuse</strong><br />{value(cache, "served")} served / {value(cache, "hits")} hits</div>
              <div className="glass-card"><strong>Validation</strong><br />{value(validation, "status")}</div>
            </div>
            <h4 style={{ marginTop: 24, marginBottom: 12 }}>Timeline</h4>
            <div className="glass-panel" style={{ padding: "0" }}>
              <table className="glass-table">
                <thead><tr><th>Event</th><th>Tool / model</th><th>Status</th><th>Duration</th><th>Cost</th></tr></thead>
                <tbody>{timeline.map((event, index) => <tr key={`${event.timestamp ?? "event"}-${index}`}><td>{event.event_type}</td><td>{event.tool_name ?? event.model_name ?? "—"}</td><td>{event.status ?? "—"}</td><td>{event.duration_ms == null ? "—" : `${event.duration_ms} ms`}</td><td>{event.cost_usd == null ? "—" : `$${event.cost_usd.toFixed(4)}`}</td></tr>)}</tbody>
              </table>
            </div>
          </>}
        </section>
      </div>
    </div>
  );
}
