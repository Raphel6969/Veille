import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import Overview from "./pages/Overview";
import Workflows from "./pages/Workflows";
import RunExplorer from "./pages/RunExplorer";
import Connections from "./pages/Connections";
import Adapters from "./pages/Adapters";
import Policies from "./pages/Policies";

const links = [
  { to: "/", label: "Overview" },
  { to: "/workflows", label: "Workflows" },
  { to: "/runs", label: "Run Explorer" },
  { to: "/connections", label: "Connections" },
  { to: "/adapters", label: "Adapters" },
  { to: "/policies", label: "Policies" },
];

export default function App() {
  return (
    <BrowserRouter>
      <nav style={{ display: "flex", gap: 12, padding: 8, background: "#f5f5f5" }}>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === "/"}
            style={({ isActive }) => ({
              fontWeight: isActive ? 700 : 400,
              textDecoration: "none",
            })}
          >
            {l.label}
          </NavLink>
        ))}
      </nav>
      <main style={{ padding: 16, fontFamily: "system-ui, sans-serif" }}>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/workflows" element={<Workflows />} />
          <Route path="/runs" element={<RunExplorer />} />
          <Route path="/connections" element={<Connections />} />
          <Route path="/adapters" element={<Adapters />} />
          <Route path="/policies" element={<Policies />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
