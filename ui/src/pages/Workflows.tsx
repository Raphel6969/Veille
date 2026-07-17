import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import * as api from "../api";

export default function Workflows() {
  const [wfs, setWfs] = useState<api.WorkflowInfo[]>([]);
  const [scenarios, setScenarios] = useState<Record<string, string>>({});
  const [running, setRunning] = useState<string | null>(null);
  const [result, setResult] = useState<api.RunView | null>(null);
  const navigate = useNavigate();

  useEffect(() => { api.workflows().then(setWfs).catch(() => {}); }, []);

  const scenarioFor = (workflow: api.WorkflowInfo) =>
    scenarios[workflow.name] ?? workflow.scenarios[0] ?? "success";

  const run = async (workflow: api.WorkflowInfo) => {
    setRunning(workflow.name);
    setResult(null);
    try {
      setResult(await api.runWorkflow(workflow.name, scenarioFor(workflow)));
    } catch (error: unknown) {
      alert(error instanceof Error ? error.message : "Workflow execution failed.");
    } finally {
      setRunning(null);
    }
  };

  return (
    <div>
      <h2>Workflows</h2>
      <p style={{ color: "#475467" }}>Choose the scenario, run it, then open its evidence in Run Explorer.</p>
      {wfs.map((workflow) => (
        <div key={workflow.name} style={{ border: "1px solid #ccc", margin: "8px 0", padding: 12, background: "#fff" }}>
          <strong>{workflow.name}</strong> <em>({workflow.framework})</em>
          <p>{workflow.description}</p>
          <label>
            Scenario{" "}
            <select
              value={scenarioFor(workflow)}
              onChange={(event) => setScenarios({ ...scenarios, [workflow.name]: event.target.value })}
              disabled={running !== null}
            >
              {workflow.scenarios.map((scenario) => <option key={scenario} value={scenario}>{scenario}</option>)}
            </select>
          </label>{" "}
          <button onClick={() => run(workflow)} disabled={running !== null}>
            {running === workflow.name ? "Running..." : "Run workflow"}
          </button>
        </div>
      ))}
      {result && (
        <div style={{ marginTop: 16, padding: 12, background: "#ecfdf3", border: "1px solid #abefc6" }}>
          <strong>Run captured:</strong> {result.run_id}
          <div style={{ marginTop: 8 }}>
            <button onClick={() => navigate(`/runs?selected=${result.run_id}`)}>View evidence in Run Explorer</button>
          </div>
        </div>
      )}
    </div>
  );
}
