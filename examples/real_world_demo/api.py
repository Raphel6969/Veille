"""Read-only demo API for the real-world supervisor demo.

A genuinely read-only HTTP service (stdlib only) that serves a small curated
dataset of AI-runtime-supervision competitors and their cited sources. No
writes, no external network, no secrets. If ``SUPERVISOR_DEMO_API_URL`` is set,
the client talks to that endpoint instead (still expected to be read-only).

The point is to exercise the Supervisor against *real* HTTP tool calls with real
latency and a real cost model, so cache hits and savings are meaningful — while
remaining safe to run anywhere (CI, laptop, design-partner laptop).
"""
from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

DATASET: dict[str, Any] = {
    "competitors": [
        {"id": "langchain", "name": "LangChain", "focus": "orchestration", "vendor_neutral": True},
        {"id": "langgraph", "name": "LangGraph", "focus": "stateful orchestration",
         "vendor_neutral": True},
        {"id": "agentops", "name": "AgentOps", "focus": "agent observability",
         "vendor_neutral": True},
        {"id": "langsmith", "name": "LangSmith", "focus": "tracing/eval",
         "vendor_neutral": False},
        {"id": "arize_phoenix", "name": "Arize Phoenix", "focus": "LLM observability",
         "vendor_neutral": True},
    ],
    "sources": {
        "s1": {"id": "s1", "title": "2026 State of Agent Ops", "url": "https://example.com/s1",
               "published": "2026-03-01",
               "content": "Vendor-neutral survey of agent supervision tooling."},
        "s2": {"id": "s2", "title": "Runtime Guardrails Comparison", "url": "https://example.com/s2",
               "published": "2026-05-12",
               "content": "Comparison of runtime guardrail approaches."},
    },
}

PER_CALL_COST_USD = 0.002  # modeled cost per API call (the API itself is free)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:  # silence noisy logs in demo
        return

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # read-only: only GET is served
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/search":
            q = (params.get("q", [""])[0] or "").lower()
            results = [
                c for c in DATASET["competitors"]
                if q in c["name"].lower() or q in c["focus"].lower()
            ]
            self._json({"query": q, "results": results})
        elif parsed.path == "/source":
            sid = params.get("id", [""])[0]
            src = DATASET["sources"].get(sid)
            if src is None:
                self._json({"error": "not_found"}, status=404)
            else:
                self._json(src)
        else:
            self._json({"error": "not_found"}, status=404)

    def do_POST(self) -> None:  # explicitly reject writes
        self._json({"error": "read_only"}, status=405)


class CompetitorAPI:
    """Read-only client. Starts a local server unless an external URL is provided."""

    def __init__(self, base_url: str | None = None) -> None:
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        if base_url:
            self.base_url = base_url.rstrip("/")
        else:
            self._server, port = _start_server()
            self.base_url = f"http://127.0.0.1:{port}"

    def search(self, query: str) -> dict[str, Any]:
        return self._get("/search", q=query)

    def fetch_source(self, source_id: str) -> dict[str, Any]:
        return self._get("/source", id=source_id)

    def _get(self, path: str, **params: str) -> dict[str, Any]:
        url = self.base_url + path + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=5) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        return data

    def close(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            if self._thread is not None:
                self._thread.join(timeout=2)


def _start_server() -> tuple[ThreadingHTTPServer, int]:
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port
