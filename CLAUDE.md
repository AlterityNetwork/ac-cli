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
ac crm search <query>        # Search companies, contacts, deals
ac crm companies list|get|create|update|delete
ac crm people list|get|create|update|delete
ac crm deals list|get|create|update|move|delete
ac crm activities list|get|create|complete|delete
ac crm comms list|get|thread|unread|mark-read|delete|delete-thread
ac crm dashboard [--period N]
ac crm lists list|get|create|members|add-member|remove-member|delete
```

All CRM list/get commands support `--json` flag for scripting (set on `ac crm --json`). The flag is passed via `typer.Context` (not a global variable).

## Running Checks

```bash
uv run pytest              # Run all tests (85 tests)
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
