import { useEffect, useState } from "react";
import * as api from "../api";

export default function Adapters() {
  const [items, setItems] = useState<api.AdapterInfo[]>([]);

  useEffect(() => { api.adapters().then(setItems).catch(() => {}); }, []);

  return (
    <div>
      <h2>Adapters</h2>
      <table>
        <thead><tr><th>Name</th><th>Status</th><th>Description</th></tr></thead>
        <tbody>
          {items.map((a) => (
            <tr key={a.name}>
              <td>{a.name}</td>
              <td>{a.status}</td>
              <td>{a.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
