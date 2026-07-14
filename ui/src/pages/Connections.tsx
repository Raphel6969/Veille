import { useEffect, useState } from "react";
import * as api from "../api";

export default function Connections() {
  const [conns, setConns] = useState<api.ConnectionInfo[]>([]);
  const [status, setStatus] = useState<Record<string, string>>({});

  useEffect(() => { api.connections().then(setConns).catch(() => {}); }, []);

  const validate = async (provider: string) => {
    setStatus((s) => ({ ...s, [provider]: "validating..." }));
    try {
      const r = await api.validateConnection(provider);
      setStatus((s) => ({ ...s, [provider]: r.ok ? "OK" : `FAIL: ${r.reason}` }));
    } catch {
      setStatus((s) => ({ ...s, [provider]: "error" }));
    }
  };

  return (
    <div>
      <h2>Connections</h2>
      <table>
        <thead>
          <tr><th>Provider</th><th>Status</th><th>Env Var</th><th>Key</th><th>Models</th><th></th></tr>
        </thead>
        <tbody>
          {conns.map((c) => (
            <tr key={c.provider}>
              <td>{c.provider}</td>
              <td>{c.status}</td>
              <td>{c.env_var}</td>
              <td>{c.masked_key ?? "(not set)"}</td>
              <td>{c.supported_models.join(", ")}</td>
              <td>
                <button onClick={() => validate(c.provider)}>Validate</button>
                {status[c.provider] && <span> {status[c.provider]}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
