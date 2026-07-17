# Adoption Foundation

## Golden Rule

VEILLE has one Runtime Supervisor and many entry points. SDK, CLI, IDE, and
daemon integrations converge into the Runtime Supervisor; features are
implemented once in the runtime and exposed through thin adapters.

## Current entry points

| Entry point | Status | Runtime behavior |
|---|---|---|
| `import veille` | Implemented | Re-exports the existing `Supervisor` runtime for explicit control. |
| `veille exec app.py` | Implemented | Runs a Python script with normal `__main__` semantics in an observe-mode runtime envelope. |
| Local console | Implemented | Calls registered workflows through the same SDK/runtime. |
| IDE integration | Planned | Must launch or inspect runtime runs; it must not own policy logic. |
| Daemon host | Planned | Must host/export the same normalized event and policy path. |

## `veille exec` boundary

`veille exec` deliberately does not monkeypatch an application's providers,
tools, or frameworks. It produces a normalized lifecycle trace without changing
business behavior. Detailed model/tool instrumentation becomes available when
the app uses `import veille` or an approved framework adapter.
