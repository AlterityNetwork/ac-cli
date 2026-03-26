# ac-cli

Python CLI for AgencyCore. Built with Typer + httpx + Rich + Supabase auth.

## Setup

```bash
uv sync                    # Install all dependencies
uv sync --all-extras       # Install with dev dependencies (pytest, respx)
```

## Command Groups

`ac <group> <subcommand> [--json]` — all commands support `--json` for scripting.

| Group | Domain |
|-------|--------|
| `crm` | Companies, people, deals, activities, comms, lists, imports |
| `envoy` | Sequences, steps, recipients, outbox, playbooks, battlecards, inbox |
| `files` | Image upload/delete |
| `workflows` | Runs, schedules, presets |
| `apps` | Organization app install/config |
| `admin` | Users, orgs, queues, demo, onboarding, app-usage, ai-usage (super admin) |
| `styles` | Writing styles |
| `nylas` | Email integration |
| `hooks` | Platform hooks |
| `health` | Health checks |
| `env` | Environment switching (local, staging, production) |

Run `ac <group> --help` for full subcommand listing.

## Agent-Friendly Features

The CLI is designed to be consumed by AI agents and scripts:

- **Structured JSON errors**: When `--json` is active, errors return `{"error": true, "status_code": ..., "detail": ...}` instead of Rich text
- **Semantic exit codes**: `0`=success, `1`=general error, `2`=validation (422), `3`=not found (404), `4`=auth/permission (401/403), `5`=conflict (409)
- **`AC_YES=1` env var**: Skips all `typer.confirm()` prompts for non-interactive use
- **`--json` on all groups**: Every group callback calls `set_json_mode()` so errors also respect JSON mode

See `.claude/rules/code-patterns.md` for implementation details.

## Running Checks

```bash
uv run pytest                              # All tests
uv run pytest tests/test_crm_companies.py  # Single file
uv run python -m ac_cli.main --help        # Verify CLI loads
```

## Critical Rules

- **Never hardcode a version** — managed by hatch-vcs from git tags. See `.claude/rules/versioning.md`.
- **Always use conventional commit prefixes** (`feat:`, `fix:`, `chore:`, etc.) — auto-bump and PyPI publishing depend on this.
- **Credentials in `~/.agencycore/config.json`** (file mode 0600) — never commit.
- **Dependencies**: use `uv add <pkg>` / `uv add --dev <pkg>`. Both `pyproject.toml` and `uv.lock` must stay in sync.
