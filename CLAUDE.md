# ac-cli

Python CLI for AgencyCore. Built with Typer + httpx + Rich + Supabase auth.

## Setup

```bash
uv sync                    # Install all dependencies
uv sync --all-extras       # Install with dev dependencies (pytest, respx)
```

## Commands

```
ac login / logout / whoami   # Auth commands
ac health check              # API health (no auth)

# CRM
ac crm search <query>        # Search companies, contacts, deals
ac crm companies list|get|create|update|delete
ac crm people list|get|create|update|delete
ac crm deals list|get|create|update|move|order|delete
ac crm activities list|get|create|update|complete|delete
ac crm comms list|get|thread|unread|mark-read|delete|delete-thread|update|archive|unarchive|contact-by-email|resolve-contact|draft-email|generate-draft|unread-thread-ids
ac crm dashboard [--period N]
ac crm lists list|get|create|update|members|add-member|remove-member|delete
ac crm import preview|commit

# Envoy (outreach)
ac envoy sequences list|get|create|update|delete|launch|pause|resume
ac envoy steps create|update|delete|reorder|stats
ac envoy recipients list|add|remove
ac envoy outbox pending|sent|step-drafts|update-draft|approve|reject|regenerate
ac envoy dashboard
```

All CRM and Envoy commands support `--json` flag for scripting (set on `ac crm --json` or `ac envoy --json`). The flag is passed via `typer.Context`.

## Running Checks

```bash
uv run pytest              # Run all tests (165 tests)
uv run pytest tests/test_crm_companies.py -v  # Single test file
uv run python -m ac_cli.main --help            # Verify CLI loads
```

## Dependency Management

Uses **uv** for dependency management. Both `pyproject.toml` and `uv.lock` must stay in sync.

```bash
uv add <package>           # Add a dependency
uv add --dev <package>     # Add a dev dependency
uv lock                    # Regenerate lockfile after manual pyproject.toml edits
```

## Config

Credentials stored in `~/.agencycore/config.json` (file mode 0600).

### Environments

`ac login` defaults to **staging**. Use `--dev` for local development:

```bash
ac login              # Staging (api.agencycore.dev)
ac login --dev        # Local dev (localhost:8008 + local Supabase)
```

Environment constants (URLs, anon keys) are defined in `config.py`:
- `STAGING_*` — staging API + Supabase
- `DEV_*` — localhost API + local Supabase (`127.0.0.1:54321`)
