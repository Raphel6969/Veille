# Security and Privacy

## Defaults (Phase 0)

- **No secrets in source, logs, fixtures, or documentation.**
- `.env` is gitignored; `.env.example` documents opt-in keys only.
- Trace fixtures store metadata and hashes, not full prompts or PII.
- Mock execution by default; paid API calls require explicit opt-in.

## Secrets handling

| Rule | Implementation |
|---|---|
| Never commit credentials | `.gitignore` includes `.env` |
| Never print keys in logs | Mock adapter avoids external calls |
| Document opt-in only | `.env.example` comments for API keys |

## Data retention (planned)

| Data type | Phase 0 | Future |
|---|---|---|
| Run metadata | In-memory / JSON fixtures | Postgres with retention policy |
| Raw prompts | Not stored | Explicit opt-in with redaction |
| Tool payloads | Hash + preview only | Configurable retention |
| Replay artifacts | Local JSON | MinIO with retention controls |

## Redaction

Phase 1+ will redact sensitive fields before persistence. Event `attributes` should use `prompt_preview` (truncated) rather than full content.

## Access control (planned Phase 5)

- RBAC for policy changes and enforcement enablement
- Audit logs for material decisions
- Tenant isolation for multi-team deployments

## Reporting issues

Do not include production traces or API keys in bug reports. Use synthetic fixtures from `fixtures/traces/`.
