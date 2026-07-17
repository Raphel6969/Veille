import { useEffect, useState } from "react";
import * as api from "../api";

export default function Preflight() {
  const [proposal, setProposal] = useState<api.PreflightProposal | null>(null);
  const [approved, setApproved] = useState(false);
  
  useEffect(() => { 
    api.preflight("examples/cited_market_research/task_contract.yaml", ["Research question: competitors", "Source list: approved evidence"])
      .then(setProposal)
      .catch(() => {}); 
  }, []);
  
  if (!proposal) return <p className="text-subtle">Preparing advisory plan…</p>;
  
  return (
    <section style={{ maxWidth: 1080, margin: "24px auto" }}>
      <p className="text-subtle" style={{ letterSpacing: ".08em", textTransform: "uppercase", fontSize: 12 }}>
        Preflight review · {proposal.status}
      </p>
      <h1 style={{ fontSize: 36, margin: "8px 0 28px", letterSpacing: "-.04em" }}>Decide before the run.</h1>
      
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr .8fr", gap: 16 }}>
        <div className="glass-card" style={{ padding: 20 }}>
          <h3>Execution plan</h3>
          {proposal.execution_plan.steps.map(s => (
            <div key={s.step_id} style={{ padding: "12px 0", borderTop: "1px solid var(--border-color)" }}>
              <b style={{ color: "var(--text-accent)" }}>{s.role}</b>
              <div className="text-subtle">{s.description}</div>
            </div>
          ))}
        </div>
        
        <div className="glass-card" style={{ padding: 20 }}>
          <h3>Recommended tier</h3>
          <div style={{ fontSize: 26, textTransform: "capitalize", color: "var(--text-accent)" }}>
            {proposal.execution_plan.selected_tier.replace("_", " ")}
          </div>
          {proposal.cost_options.filter(c => c.recommended).map(c => (
            <p key={c.tier} className="text-subtle">
              ${c.estimated_cost_usd_min}–${c.estimated_cost_usd_max} estimated
            </p>
          ))}
        </div>
      </div>
      
      <div style={{ marginTop: 24, marginBottom: 24 }}>
        <button 
          className="glass-button active"
          onClick={() => api.runWorkflow("cited_market_research", "success", true).then(() => setApproved(true))} 
          style={{ padding: "12px 24px", fontSize: "16px" }}
        >
          Approve & run safe demo
        </button>
        {approved && <span style={{ marginLeft: 16, color: "var(--text-accent)" }}>Approved run started through the shared runtime.</span>}
      </div>
      
      <div className="glass-card" style={{ padding: 20 }}>
        <h3>Role context & routes</h3>
        {proposal.context_manifests.map(m => { 
          const route = proposal.route_recommendations.find(r => r.step_id === m.step_id); 
          return (
            <div key={m.step_id} style={{ padding: "14px 0", borderTop: "1px solid var(--border-color)" }}>
              <b style={{ color: "var(--text-accent)" }}>{m.role}</b> 
              <span className="text-subtle"> → {route?.model}</span>
              <p className="text-subtle" style={{ marginBottom: 0, marginTop: 4 }}>{m.reason}</p>
            </div>
          ); 
        })}
      </div>
    </section>
  );
}
