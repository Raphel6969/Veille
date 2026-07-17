import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import * as api from "../api";
import { Dropdown } from "../components/Dropdown";

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
      <p className="text-subtle">Choose the scenario, run it, then open its evidence in Run Explorer.</p>
      {wfs.map((workflow) => (
        <div key={workflow.name} className="glass-card" style={{ marginBottom: 16 }}>
          <strong>{workflow.name}</strong> <em className="text-subtle">({workflow.framework})</em>
          <p>{workflow.description}</p>
          <label className="text-subtle" style={{ marginRight: 12, display: "inline-flex", alignItems: "center", gap: 8 }}>
            Scenario
            <Dropdown
              value={scenarioFor(workflow)}
              options={workflow.scenarios}
              onChange={(val) => setScenarios({ ...scenarios, [workflow.name]: val })}
              disabled={running !== null}
            />
          </label>
          <button className="glass-button" onClick={() => run(workflow)} disabled={running !== null}>
            {running === workflow.name ? "Running..." : "Run workflow"}
          </button>
        </div>
      ))}
      {result && (
        <div className="glass-alert" style={{ marginTop: 16, borderColor: "rgba(16, 185, 129, 0.3)", color: "#34d399", background: "rgba(16, 185, 129, 0.1)" }}>
          <strong style={{ color: "#fff" }}>Run captured:</strong> {result.run_id}
          <div style={{ marginTop: 12 }}>
            <button className="glass-button" onClick={() => navigate(`/runs?selected=${result.run_id}`)}>View evidence in Run Explorer</button>
          </div>
        </div>
      )}
    </div>
  );
}
