# ac-cli

Python CLI for AgencyCore. Built with Typer + httpx + Rich + Supabase auth.

## Setup

```bash
uv sync                    # Install all dependencies
uv sync --all-extras       # Install with dev dependencies (pytest, respx)
```

## Commands

```
ac --version / -V            # Show version
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
ac envoy playbooks list|get|create|update|delete|duplicate
ac envoy battlecards list|get|create|update|delete|duplicate
ac envoy inbox list|messages|archive|unarchive|assign|snooze|complete|update-status|add-tags|remove-tags|reply
ac envoy signals <recipient-id>
ac envoy inbox-count
ac envoy dashboard

# Writing Styles
ac styles list|get|create|update|delete|train|feedback|iterate|analyze

# Workflows
ac workflows runs create|list|get|logs
ac workflows schedules list|get|create|update|delete|preview|toggle
ac workflows presets list|get|create|update|delete

# Organization Apps
ac apps install|uninstall|list|usage-event|usage|configs|update-config|delete-config

# Admin (super admin only)
ac admin users list|get|create|update|delete|search|reset-password|impersonate|exit-impersonation|generate-link
ac admin orgs list|get|create|update|delete|members|add-member|update-member|remove-member|transfer-ownership
ac admin queues health|stats|queue-stats|metrics|send-to-sentry|job-performance|failed|retry-all|retry-job|clear-failed
ac admin demo scrape-website|generate-org|generate-profile|prepare-account|list-accounts|get-account|update-account|delete-account|cleanup|stats

# Nylas (email integration)
ac nylas oauth-start|account|org-accounts|disconnect|send|update-signature|validate-signature

# Hooks
ac hooks list <capability>
```

All commands support `--json` flag for scripting (set on the group, e.g. `ac crm --json` or `ac admin --json`). The flag is passed via `typer.Context`.

## Running Checks

```bash
uv run pytest              # Run all tests (~334 tests)
uv run pytest tests/test_crm_companies.py -v  # Single test file
uv run python -m ac_cli.main --help            # Verify CLI loads
```

## Versioning

Version is managed by **hatch-vcs** — derived from git tags automatically.

- **Never hardcode a version** in `pyproject.toml` (it uses `dynamic = ["version"]`)
- `src/ac_cli/_version.py` is auto-generated at build time — **do not edit or commit it** (gitignored)
- `__version__` is exposed via `ac_cli.__version__` and the `ac --version` flag

### Auto-bump (post-commit hook)

A post-commit hook (`scripts/auto-version-tag.sh`) auto-creates a version tag based on **conventional commit** prefixes:

| Commit prefix | Bump | Example |
|---------------|------|---------|
| `feat:` | minor | 0.1.0 → 0.2.0 |
| `fix:`, `perf:` | patch | 0.1.0 → 0.1.1 |
| `feat!:`, `fix!:`, `BREAKING CHANGE` | major | 0.1.0 → 1.0.0 |
| `chore:`, `docs:`, `refactor:`, `test:`, `ci:`, `style:`, `build:` | none | no tag created |

Add `[skip-version]` to a commit message to skip auto-tagging.

Install the hook: `bash .claude/hooks/install-submodule-hooks.sh` (from the parent repo).

### Manual bump

```bash
./scripts/bump.sh patch    # 0.1.0 → 0.1.1
./scripts/bump.sh minor    # 0.1.0 → 0.2.0
./scripts/bump.sh major    # 0.1.0 → 1.0.0
./scripts/bump.sh minor --push  # bump + push tag to remote
```

Between tags, dev builds show versions like `0.2.1.dev3+gabcdef1`.

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
