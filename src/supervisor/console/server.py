"""FastAPI backend for the Veille Local Integration Console web UI.

Thin wrapper over the existing runtime, explorer, registry, and connection
modules. Every endpoint operates through the supervisor runtime — there is no
second runtime and no secret is ever returned in a response body.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from supervisor.console.config import get_settings
from supervisor.console.connections import list_connections, validate_connection
from supervisor.console.doctor import doctor_payload
from supervisor.console.explorer import explore
from supervisor.console.run_registry import (
    get_workflow,
    list_adapters,
    list_runs,
    list_workflows,
    load_run,
    run_workflow,
)
from supervisor.contracts.events import RunEventBatch
from supervisor.contracts.preflight import ContextSource, PreflightRequest
from supervisor.io import load_task_contract, save_trace_fixture
from supervisor.sdk import Supervisor

app = FastAPI(title="Veille Local Integration Console", version="0.1.0")

# Mount packaged React assets when available (must be before the catch-all route).
# The repository path is retained solely for `npm run dev` / local builds.
_PACKAGED_UI_DIR = Path(__file__).resolve().parent / "ui"
_REPOSITORY_UI_DIR = Path(__file__).resolve().parents[3] / "ui" / "dist"
_UI_DIR = _PACKAGED_UI_DIR if _PACKAGED_UI_DIR.is_dir() else _REPOSITORY_UI_DIR
_UI_READY = _UI_DIR.is_dir()
if _UI_READY:
    app.mount("/assets", StaticFiles(directory=str(_UI_DIR / "assets")), name="ui-assets")
else:
    print(
        "React UI not found at ui/dist/. Run `cd ui && npm run build` to build it, "
        "or use `npm run dev` (port 5173) during development.",
        flush=True,
    )


class RunRequest(BaseModel):
    scenario: str = "success"
    real: bool = False
    confirm: bool = False
    apply_preflight: bool = False


class PreflightConsoleRequest(BaseModel):
    task_contract_path: str
    context: list[str] = []


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/doctor")
def doctor() -> dict[str, Any]:
    return doctor_payload()


@app.get("/api/connections")
def connections() -> list[dict[str, Any]]:
    return [asdict(c) for c in list_connections()]


@app.get("/api/connections/{provider}/validate")
def validate(provider: str, real: bool = False) -> dict[str, Any]:
    ok, reason = validate_connection(provider, real=real)
    return {"provider": provider, "ok": ok, "reason": reason}


@app.get("/api/workflows")
def workflows() -> list[dict[str, Any]]:
    return [
        {
            "name": w.name,
            "description": w.description,
            "framework": w.framework,
            "supports_real": w.supports_real,
            "read_only_tools": w.read_only_tools,
            "scenarios": w.default_scenarios,
        }
        for w in list_workflows()
    ]


@app.get("/api/workflows/{name}")
def workflow_detail(name: str) -> dict[str, Any]:
    wf = get_workflow(name)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Unknown workflow: {name}")
    return {
        "name": wf.name,
        "description": wf.description,
        "framework": wf.framework,
        "supports_real": wf.supports_real,
        "read_only_tools": wf.read_only_tools,
        "scenarios": wf.default_scenarios,
    }


@app.post("/api/preflight")
def preflight_endpoint(req: PreflightConsoleRequest) -> dict[str, Any]:
    try:
        task = load_task_contract(req.task_contract_path)
        proposal = Supervisor(task).preflight(
            PreflightRequest(
                task_contract=task,
                master_context=[
                    ContextSource(source_id=str(i), content=value)
                    for i, value in enumerate(req.context)
                ],
            )
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return cast(dict[str, Any], proposal.model_dump(mode="json"))


@app.post("/api/workflows/{name}/run")
def run_workflow_endpoint(name: str, req: RunRequest) -> dict[str, Any]:
    settings = get_settings()
    if req.real and not req.confirm:
        raise HTTPException(status_code=400, detail="Real execution requires confirm=true.")
    if req.apply_preflight and not req.confirm:
        raise HTTPException(status_code=400, detail="Preflight application requires confirm=true.")
    if settings.real_mode and req.real is False:
        # honor console real-mode only when explicitly requested
        pass
    try:
        result = run_workflow(name, scenario=req.scenario, apply_preflight=req.apply_preflight)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    batch: RunEventBatch = result["batch"]
    save_trace_fixture(batch, Path("fixtures/traces") / f"{batch.run_id}.json")
    return explore(batch)


@app.get("/api/providers")
def providers() -> list[str]:
    return [c.provider for c in list_connections(real_mode=get_settings().real_mode)]


@app.get("/api/adapters")
def adapters() -> list[dict[str, Any]]:
    return [
        {"name": a.name, "status": a.status, "description": a.description} for a in list_adapters()
    ]


@app.get("/api/runs")
def runs() -> list[dict[str, Any]]:
    return [{"run_id": r.run_id, "task_id": r.task_id, "scenario": r.scenario} for r in list_runs()]


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str) -> dict[str, Any]:
    try:
        return explore(load_run(run_id))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# SPA catch-all — serve index.html for any non-API path (must be last).
if _UI_READY:

    @app.get("/{full_path:path}")
    async def serve_ui(full_path: str) -> FileResponse:
        file_path = _UI_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_UI_DIR / "index.html"))
