import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import Overview from "./pages/Overview";
import Workflows from "./pages/Workflows";
import RunExplorer from "./pages/RunExplorer";
import Connections from "./pages/Connections";
import Adapters from "./pages/Adapters";
import Policies from "./pages/Policies";
import Preflight from "./pages/Preflight";

const links = [
  { to: "/", label: "Overview" },
  { to: "/workflows", label: "Workflows" },
  { to: "/runs", label: "Run Explorer" },
  { to: "/connections", label: "Connections" },
  { to: "/adapters", label: "Adapters" },
  { to: "/policies", label: "Policies" },
  { to: "/preflight", label: "Preflight" },
];

export default function App() {
  return (
    <BrowserRouter>
      <nav className="glass-panel" style={{ display: "flex", gap: 18, padding: "14px 28px", margin: "16px", borderBottom: "none", alignItems: "center" }}>
        <strong style={{ marginRight: "16px", color: "var(--text-primary)" }}>Veille</strong>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === "/"}
            className="nav-link"
          >
            {l.label}
          </NavLink>
        ))}
      </nav>
      <main style={{ minHeight: "calc(100vh - 84px)", padding: "0 16px 16px 16px" }}>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/workflows" element={<Workflows />} />
          <Route path="/runs" element={<RunExplorer />} />
          <Route path="/connections" element={<Connections />} />
          <Route path="/adapters" element={<Adapters />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/preflight" element={<Preflight />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
