#!/usr/bin/env bash
set -euo pipefail

# ── Veille Installer — macOS / Linux / WSL ──────────────────────────────

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python not found. Install Python 3.12+ from https://python.org and try again." >&2
    exit 1
fi

PYVER=$($PYTHON --version 2>&1)
if echo "$PYVER" | grep -qE '3\.(1[2-9]|[2-9]\d)'; then
    echo "✓ $PYVER"
else
    echo "ERROR: Python 3.12+ required. Found $PYVER" >&2
    exit 1
fi

echo "Installing veille-supervisor..."
$PYTHON -m pip install --upgrade pip -q
pip install veille-supervisor -q

ENV_PATH="$HOME/.veille.env"
if [ ! -f "$ENV_PATH" ]; then
    read -rp "Create default .env at $ENV_PATH? [Y/n] " COPY
    if [ "$COPY" != "n" ]; then
        cat > "$ENV_PATH" <<'EOF'
VEILLE_REAL_MODE=false
VEILLE_CACHE_BACKEND=memory
LOG_LEVEL=INFO
EOF
        echo "✓ Created $ENV_PATH"
    fi
fi

echo ""
echo "--- Verification ---"
veille doctor

echo ""
echo "✓ Veille is ready!"
echo "  veille doctor      —  system health"
echo "  veille demo mock   —  run mock demo"
echo "  veille serve        —  launch web UI at http://127.0.0.1:8000"
