#!/bin/bash
# Dead-code + unused-dependency scan for ac-cli.
# Runs deptry (unused/missing deps) and vulture (unused symbols).

set -e

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

FAILED=0

echo "=== deptry ==="
uv run deptry src/ || FAILED=1
echo ""

echo "=== vulture (min_confidence=80) ==="
uv run vulture || FAILED=1
echo ""

if [ "$FAILED" -ne 0 ]; then
    echo "⚠️  Issues found."
    exit 1
fi

echo "✅ Clean."
