# Local durable daemon

Start VEILLE's local pilot host with:

```powershell
veille daemon --database .veille/veille.db
```

The daemon binds to `127.0.0.1:8020` by default and exposes `/health`. Its
SQLite repository persists preflight proposals and normalized run batches. It is
local-only pilot infrastructure; authentication, multi-project isolation, and
Postgres are future hardening work.
