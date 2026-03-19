---
paths:
  - "src/**/*.py"
---

# Code Patterns

## Environment Selection
- `ac login` defaults to staging (`STAGING_*` constants in `config.py`)
- `ac login --dev` uses local dev (`DEV_*` constants in `config.py`)
- Explicit `--api-url`, `--supabase-url`, `--supabase-anon-key` flags override environment defaults

## Command Structure
- Each command group is a `typer.Typer()` sub-app registered via `app.add_typer()` in `main.py`
- All commands use `_api_request()` helper from `commands/_helpers.py` for HTTP calls with built-in error handling
- Use `_build_body()` helper from `commands/_helpers.py` to construct request bodies from non-None fields (handles tags splitting)
- Package-based domains (crm, envoy, workflows, admin) have their own `__init__.py` with prefix constant and `--json` callback
- Standalone domains (writing_styles, apps, nylas, hooks) are single-file modules with their own prefix constant and callback
- IDs are positional `typer.Argument()`, optional fields are `typer.Option(None, ...)`
- Tags: accept comma-separated string on CLI, `_build_body` splits to list automatically
- Dates: ISO format strings (`2026-03-15`)
- Standalone commands (not sub-apps) are registered via `app.command("name")(function)` — see `signals_command`, `dashboard_command` in envoy

## API Route Prefix
- Each domain defines its own prefix constant in its `__init__.py` or module file:
  - `_CRM = "/api/v1/crm"` in `crm/__init__.py`
  - `_ENVOY = "/api/v1/envoy"` in `envoy/__init__.py`
  - `_WORKFLOWS = "/api/v1/workflows"` in `workflows/__init__.py`
  - `_ADMIN = "/api/v1/admin"` in `admin/__init__.py`
  - `_STYLES = "/api/v1/writing-styles"` in `writing_styles.py`
  - `_APPS = "/api/v1/orgs"` in `apps.py`
  - `_NYLAS = "/api/v1/nylas"` in `nylas.py`
  - `_FILES = "/api/v1/files"` in `files/__init__.py`
  - `_HOOKS = "/api/v1/platform/hooks"` in `hooks.py`
- All domains share `_api_request()`, `_build_body()`, and `_handle_error()` from `commands/_helpers.py`
- Non-versioned routes (`/whoami`, `/health`) use root paths directly
- No trailing slashes on API paths

## Error Handling
- `_api_request()` catches both `httpx.HTTPStatusError` (API errors) and `httpx.HTTPError` (connection errors)
- `_handle_error()` extracts detail from API error responses and exits with code 1
- Auth and health commands handle errors directly in the command function
- `httpx.Client.delete()` does not support `json` kwarg — for DELETE requests with a JSON body, use `client.request("DELETE", url, json=...)` directly (see `inbox.py` remove-tags)

## Output
- Rich output by default via `formatting.py` helpers (`print_table`, `print_detail`)
- `--json` flag outputs raw JSON to stdout for piping/scripting
- `--json` is a global option on every command group's callback (crm, envoy, workflows, admin, styles, apps, nylas, hooks), passed via `typer.Context`
- Access in subcommands: add `ctx: typer.Context` parameter, read `ctx.obj["json"]`

## Delete Commands
- Always require `--yes` / `-y` flag or interactive `typer.confirm()` prompt

## Create Commands
- Fetch `organization_id` from `/whoami` before creating resources
- For org-scoped commands (apps), use `_resolve_org_id()` pattern — accept optional `--org-id`, fall back to `/whoami`

## Org-Scoped Commands
- Commands under `apps` require an org ID — auto-resolved from `/whoami` if `--org-id` is not specified
- The `_resolve_org_id()` helper in `apps.py` handles this pattern

## Workflow Commands
- All workflow subcommands take `workflow_id` as their first positional argument
- `runs create` returns 202 (async) — print run ID and status
- `schedules create` accepts `--cron` and `--timezone` options
- `schedules toggle` uses `--enabled`/`--disabled` flag pair

## Versioning
- Always use conventional commit prefixes (`feat:`, `fix:`, `chore:`, etc.) — the auto-bump hook and PyPI publishing depend on this. See `versioning.md` for full details.
