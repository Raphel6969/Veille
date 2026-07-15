const BASE = import.meta.env.VITE_API_URL || "";

export async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export interface DoctorPayload {
  python_version: string;
  runtime_version: string;
  installed_adapters: string[];
  registered_workflows: string[];
  registered_providers: string[];
  registered_models: string[];
  execution_mode: string;
  policy_mode: string;
  enforce_enabled: boolean;
  optimize_enabled: boolean;
  cache_approved: boolean;
  cache_backend: string;
  litellm_status: string;
  openrouter_status: string;
  router_status: string;
  warnings: string[];
}

export interface WorkflowInfo {
  name: string;
  framework: string;
  supports_real: boolean;
  description: string;
  default_scenarios: string[];
}

export interface ConnectionInfo {
  provider: string;
  env_var: string;
  key_present: boolean;
  masked_key: string | null;
  status: string;
  supported_models: string[];
}

export interface AdapterInfo {
  name: string;
  status: string;
  description: string;
}

export interface RunView {
  run_id: string;
  task_id: string;
  summary: Record<string, unknown>;
  timeline: unknown[];
  execution_graph: unknown[];
  agent_graph: unknown[];
  router: unknown;
  planner: Record<string, unknown> | null;
  estimated_vs_actual: Record<string, unknown> | null;
  context: unknown[];
  cache: Record<string, unknown>;
  validation: Record<string, unknown>;
  providers: string[];
}

export function doctor(): Promise<DoctorPayload> {
  return get<DoctorPayload>("/api/doctor");
}

export function workflows(): Promise<WorkflowInfo[]> {
  return get<WorkflowInfo[]>("/api/workflows");
}

export function connections(): Promise<ConnectionInfo[]> {
  return get<ConnectionInfo[]>("/api/connections");
}

export function validateConnection(provider: string, real = false): Promise<{ provider: string; ok: boolean; reason: string }> {
  return get(`/api/connections/${provider}/validate?real=${real}`);
}

export function providers(): Promise<string[]> {
  return get<string[]>("/api/providers");
}

export function adapters(): Promise<AdapterInfo[]> {
  return get<AdapterInfo[]>("/api/adapters");
}

export function runs(): Promise<RunView[]> {
  return get<RunView[]>("/api/runs");
}

export function runDetail(runId: string): Promise<RunView> {
  return get<RunView>(`/api/runs/${runId}`);
}

export function runWorkflow(name: string, scenario = "success", apply_preflight = false): Promise<RunView> {
  return post<RunView>(`/api/workflows/${name}/run`, { scenario, apply_preflight, confirm: apply_preflight });
}

export interface PreflightProposal { proposal_id: string; status: string; execution_plan: { selected_tier: string; steps: { step_id: string; role: string; description: string }[] }; cost_options: { tier: string; estimated_cost_usd_min: number; estimated_cost_usd_max: number; recommended: boolean }[]; context_manifests: { step_id: string; role: string; included: string[]; excluded: string[]; compressed: string[]; reason: string }[]; route_recommendations: { step_id: string; model: string; reason: string }[]; }

export function preflight(task_contract_path: string, context: string[]): Promise<PreflightProposal> {
  return post<PreflightProposal>("/api/preflight", { task_contract_path, context });
}
