# ac-cli

Python CLI for AgencyCore. Built with Typer + httpx + Rich + Supabase auth.

## Setup

```bash
uv sync                    # Install all dependencies
uv sync --all-extras       # Install with dev dependencies (pytest, respx)
```

## Command Groups

`ac <group> [--json] <subcommand>` — all groups support `--json` for scripting.

| Group | Domain |
|-------|--------|
| `crm` | Companies, people, deals, activities, comms, lists, imports |
| `envoy` | Sequences, steps, recipients, outbox, playbooks, battlecards, inbox |
| `files` | Image upload/delete |
| `workflows` | Runs, schedules, presets |
| `apps` | Organization app install/config |
| `admin` | Users, orgs, queues, demo, onboarding (super admin) |
| `styles` | Writing styles |
| `nylas` | Email integration |
| `hooks` | Platform hooks |
| `env` | Environment switching (local, staging, production) |

Run `ac <group> --help` for full subcommand listing.

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
