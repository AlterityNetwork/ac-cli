"""Copies the committed ac-python-api OpenAPI spec into this repo (ENG-3053).

CI runs the contract audits against `contracts/ac-python-api.openapi.json`.
The API repo is private and this repo holds no token that reads it, so the
spec travels as a file. Run this script after the API merges a route change,
from the monorepo layout where `../ac-python-api` is the API checkout.

Usage:
    uv run python scripts/sync_api_spec.py                 # copy
    uv run python scripts/sync_api_spec.py --check         # exit 1 when it differs
    uv run python scripts/sync_api_spec.py --from <path>   # copy from another file
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "contracts" / "ac-python-api.openapi.json"
DEFAULT_SOURCE = ROOT.parent / "ac-python-api" / "openapi.json"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if not args.source.exists():
        print(f"no spec at {args.source}", file=sys.stderr)
        return 2
    fresh = args.source.read_text()
    if args.check:
        if not TARGET.exists() or TARGET.read_text() != fresh:
            print(f"{TARGET.relative_to(ROOT)} differs from {args.source}", file=sys.stderr)
            return 1
        print(f"{TARGET.relative_to(ROOT)} matches {args.source}")
        return 0
    TARGET.parent.mkdir(exist_ok=True)
    TARGET.write_text(fresh)
    print(f"Wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
