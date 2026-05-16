#!/bin/bash
# Ruff lint + format for ac-cli.
#
# Usage:
#   ./scripts/lint.sh          # check src/ and tests/
#   ./scripts/lint.sh --fix    # auto-fix (lint --fix + format)
set -e

FIX=false
if [[ "$1" == "--fix" ]]; then
    FIX=true
    shift
fi

TARGET="${*:-src/ tests/}"

if [ "$FIX" = true ]; then
    uv run ruff check --fix $TARGET
    uv run ruff format $TARGET
else
    uv run ruff check $TARGET
    uv run ruff format --check $TARGET
fi
