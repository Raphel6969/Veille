import { useEffect, useState } from "react";
import * as api from "../api";

export default function Workflows() {
  const [wfs, setWfs] = useState<api.WorkflowInfo[]>([]);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<api.RunView | null>(null);

  useEffect(() => { api.workflows().then(setWfs).catch(() => {}); }, []);

  const run = async (name: string) => {
    setRunning(true);
    setResult(null);
    try {
      setResult(await api.runWorkflow(name));
    } catch (e: any) {
      alert(e.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <h2>Workflows</h2>
      {wfs.map((w) => (
        <div key={w.name} style={{ border: "1px solid #ccc", margin: "8px 0", padding: 8 }}>
          <strong>{w.name}</strong> <em>({w.framework})</em>
          <p>{w.description}</p>
          <button onClick={() => run(w.name)} disabled={running}>
            {running ? "Running..." : `Run (${w.scenarios[0] ?? "default"})`}
          </button>
        </div>
      ))}
      {result && (
        <div style={{ marginTop: 16 }}>
          <h3>Run {result.run_id}</h3>
          <pre>{JSON.stringify(result.summary, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
