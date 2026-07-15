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
      <nav style={{ display: "flex", gap: 18, padding: "14px 28px", background: "#182230" }}>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === "/"}
            style={({ isActive }) => ({
              color: isActive ? "#ffffff" : "#aab4c4",
              fontWeight: isActive ? 700 : 500,
              textDecoration: "none",
            })}
          >
            {l.label}
          </NavLink>
        ))}
      </nav>
      <main style={{ minHeight: "calc(100vh - 52px)", padding: 16, background: "#f8f8f6", fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif" }}>
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
