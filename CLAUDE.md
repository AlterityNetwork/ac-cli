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
| `workflows` | Runs, schedules, presets, csv-parse |
| `apps` | Organization app install/config |
| `chat` | AI chat threads and messages |
| `admin` | Users, orgs, queues, demo, onboarding, app-usage, ai-usage, platform-activity, legal-docs, resources, apps (super admin) |
| `profiles` | User profile management |
| `resources` | Knowledge base resource management |
| `styles` | Writing styles |
| `nylas` | Email integration, thread sync, attachment download |
| `messaging` | Messaging platform sessions and account linking |
| `hooks` | Platform hooks |
| `health` | Health checks |
| `env` | Environment switching (local, staging, production) |
| `legal-docs` | Legal document retrieval and acceptance |
| `tos` | Terms of service config, status, acceptance |
| `marketplace` | App marketplace browsing and developer listing |
| `network` | Referrals, news, Slack invites |
| `onboarding` | Managed onboarding config and completion |

Run `ac <group> --help` for full subcommand listing.

## Agent-Friendly Features

The CLI is designed to be consumed by AI agents and scripts:

- **Structured JSON errors**: When `--json` is active, errors return `{"error": true, "status_code": ..., "detail": ...}` instead of Rich text
- **Semantic exit codes**: `0`=success, `1`=general error, `2`=validation (422), `3`=not found (404), `4`=auth/permission (401/403), `5`=conflict (409)
- **`AC_YES=1` env var**: Skips all `typer.confirm()` prompts for non-interactive use
- **`--json` on all groups**: Every group callback calls `set_json_mode()` so errors also respect JSON mode

See `.claude/rules/code-patterns.md` for implementation details.

## Project Layout

```
src/ac_cli/
  main.py              → Entry point, registers all command groups
  client.py            → Authenticated httpx client from stored config
  config.py            → Multi-env config (~/.agencycore/config.json)
  formatting.py        → Shared output (print_table, print_detail, print_json)
  commands/            → Command modules (auth, env, crm/, envoy/, admin/, etc.)
    _helpers.py        → Shared helpers (_api_request, _build_body, _get_org_id, exit codes)
tests/                 → One test file per command group (test_<domain>_<group>.py)
scripts/               → bump.sh (manual version), auto-version-tag.sh (post-commit hook)
```

## Running Checks

```bash
uv run pytest                              # All tests
uv run pytest tests/test_crm_companies.py  # Single file
uv run python -m ac_cli.main --help        # Verify CLI loads
```

No lint or type-check tooling is configured — pytest is the only check.

## TDD Workflow

For `feat:` and `fix:` changes, write tests first. See `.claude/rules/06-tdd-workflow.md`.

**Single test run:** `uv run pytest tests/test_<domain>_<group>.py -x`

**Watch mode:** `uv run ptw -- -x -q`

Every new command needs tests for: happy path, `--json` flag, error codes, and `--yes` on deletes.

## Critical Rules

- **Never hardcode a version** — managed by hatch-vcs from git tags. See `.claude/rules/versioning.md`.
- **Always use conventional commit prefixes** (`feat:`, `fix:`, `chore:`, etc.) — auto-bump and PyPI publishing depend on this.
- **Credentials in `~/.agencycore/config.json`** (file mode 0600) — never commit.
- **Dependencies**: use `uv add <pkg>` / `uv add --dev <pkg>`. Both `pyproject.toml` and `uv.lock` must stay in sync.

## API Domains Not Exposed in CLI

The following API domains are intentionally not covered by the CLI:

- `/test` — dev-only email simulation endpoints
- `/admin/demo/*-stream` — SSE streaming endpoints (not suitable for CLI)
- `/nylas/webhook` — server-side webhook handler (not user-callable)
- `/nylas/demo/*` — demo-only email simulation endpoints
