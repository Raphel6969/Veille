import { useEffect, useState } from "react";
import * as api from "../api";

export default function RunExplorer() {
  const [runList, setRunList] = useState<api.RunView[]>([]);
  const [selected, setSelected] = useState<api.RunView | null>(null);

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
              onClick={() => view(r.run_id)}
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
          <h3>Detail</h3>
          {selected && (
            <pre style={{ fontSize: 12 }}>{JSON.stringify(selected, null, 2)}</pre>
          )}
        </div>
      </div>
    </div>
  );
}
