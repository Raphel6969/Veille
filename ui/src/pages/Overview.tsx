import { useEffect, useState } from "react";
import * as api from "../api";

export default function Overview() {
  const [d, setD] = useState<api.DoctorPayload | null>(null);

  useEffect(() => {
    api.doctor().then(setD).catch(() => {});
  }, []);

  if (!d) return <p>Loading doctor info...</p>;

  return (
    <div>
      <h2>Overview</h2>
      <table>
        <tbody>
          <tr><td>Python</td><td>{d.python_version}</td></tr>
          <tr><td>Runtime</td><td>{d.runtime_version}</td></tr>
          <tr><td>Mode</td><td>{d.execution_mode}</td></tr>
          <tr><td>Policy</td><td>{d.policy_mode}</td></tr>
          <tr><td>Enforce</td><td>{String(d.enforce_enabled)}</td></tr>
          <tr><td>Optimize</td><td>{String(d.optimize_enabled)}</td></tr>
          <tr><td>Cache</td><td>{d.cache_backend} (approved={String(d.cache_approved)})</td></tr>
          <tr><td>Providers</td><td>{d.registered_providers.join(", ")}</td></tr>
          <tr><td>Adapters</td><td>{d.installed_adapters.join(", ")}</td></tr>
          <tr><td>Workflows</td><td>{d.registered_workflows.join(", ")}</td></tr>
        </tbody>
      </table>
      {d.warnings.length > 0 && (
        <div style={{ background: "#fff3cd", padding: 8, marginTop: 12 }}>
          <strong>Warnings:</strong>
          <ul>{d.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </div>
      )}
    </div>
  );
}
