# Veille Demo Agent

Run a supervised AI agent in **2 minutes** — no API keys required.

```bash
pip install veille-supervisor
python -m veille_demo_agent
```

What you'll see:
- An agent that researches + summarises under Veille's runtime supervisor
- Normalized events (model calls, tool calls, context, validation)
- Cost tracking, run lifecycle, and the full event batch

Then explore the run:
```bash
veille explore
veille doctor
veille serve   # launch the web UI at http://localhost:8010
```

## Real mode

Set `OPENAI_API_KEY` and re-run — Veille uses the real provider automatically.
