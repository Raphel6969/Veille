import { useEffect, useState } from "react";
import * as api from "../api";

const card: React.CSSProperties = { background: "#fff", border: "1px solid #e8e7e3", borderRadius: 14, padding: 20, boxShadow: "0 8px 24px rgba(20,25,35,.04)" };

export default function Preflight() {
  const [proposal, setProposal] = useState<api.PreflightProposal | null>(null);
  const [approved, setApproved] = useState(false);
  useEffect(() => { api.preflight("examples/cited_market_research/task_contract.yaml", ["Research question: competitors", "Source list: approved evidence"]).then(setProposal).catch(() => {}); }, []);
  if (!proposal) return <p style={{ color: "#667085" }}>Preparing advisory plan…</p>;
  return <section style={{ maxWidth: 1080, margin: "24px auto", color: "#182230" }}>
    <p style={{ color: "#667085", letterSpacing: ".08em", textTransform: "uppercase", fontSize: 12 }}>Preflight review · {proposal.status}</p>
    <h1 style={{ fontSize: 36, margin: "8px 0 28px", letterSpacing: "-.04em" }}>Decide before the run.</h1>
    <div style={{ display: "grid", gridTemplateColumns: "1.2fr .8fr", gap: 16 }}>
      <div style={card}><h3>Execution plan</h3>{proposal.execution_plan.steps.map(s => <div key={s.step_id} style={{ padding: "12px 0", borderTop: "1px solid #eee" }}><b>{s.role}</b><div style={{ color: "#667085" }}>{s.description}</div></div>)}</div>
      <div style={card}><h3>Recommended tier</h3><div style={{ fontSize: 26, textTransform: "capitalize" }}>{proposal.execution_plan.selected_tier.replace("_", " ")}</div>{proposal.cost_options.filter(c => c.recommended).map(c => <p key={c.tier} style={{ color: "#667085" }}>${c.estimated_cost_usd_min}–${c.estimated_cost_usd_max} estimated</p>)}</div>
    </div>
    <button onClick={() => api.runWorkflow("cited_market_research", "success", true).then(() => setApproved(true))} style={{ marginTop: 16, border: 0, borderRadius: 10, padding: "12px 16px", background: "#182230", color: "#fff", cursor: "pointer" }}>Approve & run safe demo</button>
    {approved && <span style={{ marginLeft: 12, color: "#16794b" }}>Approved run started through the shared runtime.</span>}
    <div style={{ ...card, marginTop: 16 }}><h3>Role context & routes</h3>{proposal.context_manifests.map(m => { const route = proposal.route_recommendations.find(r => r.step_id === m.step_id); return <div key={m.step_id} style={{ padding: "14px 0", borderTop: "1px solid #eee" }}><b>{m.role}</b> <span style={{ color: "#667085" }}>→ {route?.model}</span><p style={{ color: "#667085", marginBottom: 0 }}>{m.reason}</p></div>; })}</div>
  </section>;
}
