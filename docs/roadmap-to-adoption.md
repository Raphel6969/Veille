# Roadmap — from branch to real-world adoption

This document lays out the remaining work to take Veille from a working `pre_dev` branch to a shipped, tested, and shared open-source project.

## Phase 1 — Ship it (this week)

### 1. Merge `pre_dev` → `main` + tag a release

```powershell
git checkout main
git merge pre_dev
git tag v0.3.0
git push origin main --tags
```

### 2. Fix pyproject.toml for PyPI

Check package name, description, classifiers, and console script registration. Publish to **Test PyPI** first, then real PyPI.

```powershell
pip install build twine
python -m build
python -m twine upload --repository testpypi dist/*
python -m twine upload dist/*          # real PyPI
```

After this anyone can run:

```powershell
pip install veille-supervisor
veille doctor
```

### 3. Write install scripts

Create `scripts/install.ps1` (Windows) and `scripts/install.sh` (macOS / Linux / WSL / Git Bash).

Each script:
- Checks Python 3.12+ is installed
- Runs `pip install veille-supervisor`
- Prompts to copy `.env.example` → `.env`
- Prints `veille doctor` to verify
- Optionally launches `veille serve` and opens browser

| Script | One-liner |
|---|---|
| Windows PowerShell | `irm https://raw.githubusercontent.com/Raphel6969/Veille/main/scripts/install.ps1 \| iex` |
| macOS / Linux / WSL | `curl -fsSL https://raw.githubusercontent.com/Raphel6969/Veille/main/scripts/install.sh \| bash` |

---

## Phase 2 — Prove it with a real agent (week 2)

### 4. Write a real-world integration test

Create `examples/real_openai_agent/` — a tiny 2-step agent (research → summarize) that calls real OpenAI through the Supervisor SDK.

This surfaces every real issue:
- Credential plumbing (real mode, confirmation gate)
- LiteLLM wiring (model strings, api_base, api_key)
- Error handling (rate limits, timeouts)
- Cost and token tracking accuracy

### 5. Publish a standalone demo repo

Create `veille-demo-agent` (separate GitHub repo) that clones and runs in 2 minutes:

```powershell
pip install veille-supervisor
$env:OPENAI_API_KEY="sk-..."
veille run my_agent --input '{"query":"AI agent frameworks"}' --yes
```

---

## Phase 3 — CI + quality (week 2–3)

### 6. Set up GitHub Actions

```yaml
# .github/workflows/ci.yml
- uses: actions/setup-python@v5
  with: { python-version: "3.12" }
- run: pip install -e ".[dev]"
- run: ruff check src tests examples
- run: mypy src/supervisor
- run: pytest -q
```

### 7. Add CONTRIBUTING.md

Covers: one-command setup, lint/type/test gates, how to add a provider, how to add an adapter, PR checklist.

---

## Phase 4 — Share it (week 3)

### 8. Launch posts

| Channel | Content |
|---|---|
| Hacker News | "I built an open-source control plane for AI agents" |
| Reddit r/LocalLLaMA, r/MachineLearning | Single post with `irm \| iex` one-liner |
| X / Twitter | 30s video of `veille serve` + web UI |
| PyCoder's Weekly / Python Daily | Submit as open-source project |

Every post leads with the one-liner.

### 9. Gather feedback

- Create a GitHub Discussions category for "Real workflow integration"
- Tag early users and ask: what broke, what's missing, what's confusing

---

## Future (post-launch)

- Docker image (`docker run -p 8000:8000 veille`)
- CrewAI / AutoGen adapters
- Embedding-based semantic key backend
- Redis cache backend
- Web UI improvements (live stream run events, policy editor)
- VS Code extension (run `veille explore` from the editor)
