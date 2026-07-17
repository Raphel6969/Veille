import { useEffect, useState } from "react";
import * as api from "../api";

export default function Policies() {
  const [d, setD] = useState<api.DoctorPayload | null>(null);

  useEffect(() => { api.doctor().then(setD).catch(() => {}); }, []);

  if (!d) return <p>Loading policy info...</p>;

  return (
    <div>
      <h2>Policy Configuration</h2>
      <div className="glass-panel" style={{ padding: 0, overflowX: "auto" }}>
      <table className="glass-table">
        <tbody>
          <tr><td>Policy Mode</td><td>{d.policy_mode}</td></tr>
          <tr><td>Enforcement Enabled</td><td>{String(d.enforce_enabled)}</td></tr>
          <tr><td>Optimization Enabled</td><td>{String(d.optimize_enabled)}</td></tr>
          <tr><td>Cross-Run Cache Approved</td><td>{String(d.cache_approved)}</td></tr>
          <tr><td>Cache Backend</td><td>{d.cache_backend}</td></tr>
          <tr><td>Execution Mode</td><td>{d.execution_mode}</td></tr>
          <tr><td>LiteLLM Status</td><td>{d.litellm_status}</td></tr>
          <tr><td>OpenRouter Status</td><td>{d.openrouter_status}</td></tr>
          <tr><td>Router Status</td><td>{d.router_status}</td></tr>
        </tbody>
      </table>
      </div>
    </div>
  );
}
