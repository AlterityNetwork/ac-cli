---
paths:
  - "src/**/*.py"
---

# Code Patterns

## Environment Selection
- Three environments: `production` (default), `staging`, `local` — defined in `ENVIRONMENTS` dict in `config.py`
- `ac login` defaults to the currently active environment. Use `--env staging`, `--env local`, or `--env production` to target a specific environment
- `--dev` flag is a hidden deprecated alias for `--env local`
- `ac env list` shows all envs and login status, `ac env use <name>` switches instantly
- Config format is multi-env (`~/.agencycore/config.json` has `active` + `environments` keys). Old flat configs auto-migrate on first read
- `load_config()` / `save_config()` still return/accept flat dicts for the active env — all command modules are unaffected
- Explicit `--api-url`, `--supabase-url`, `--supabase-anon-key` flags override environment defaults

## Command Structure
- Each command group is a `typer.Typer()` sub-app registered via `app.add_typer()` in `main.py`
- All commands use `_api_request()` helper from `commands/_helpers.py` for HTTP calls with built-in error handling
- Use `_build_body()` helper from `commands/_helpers.py` to construct request bodies from non-None fields (handles tags splitting)
- Package-based domains (crm, envoy, workflows, admin) have their own `__init__.py` with prefix constant and a simple callback for context initialization
- Standalone domains (writing_styles, apps, nylas, hooks) are single-file modules with their own prefix constant and callback
- `--json` is a subcommand-level option (not group-level) — use `JSON_OPTION` from `_helpers.py` on each command
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
- `_handle_error()` extracts detail from API error responses. It checks both `"detail"` (FastAPI HTTPException format) and `"message"` (domain error format) fields
- When JSON mode is active (`_json_output` context var), errors emit structured JSON: `{"error": true, "status_code": <int>, "detail": <str>}`. Otherwise, errors print Rich-formatted text.
- **Semantic exit codes** via `_EXIT_CODES` mapping: `{401: 4, 403: 4, 404: 3, 409: 5, 422: 2}`. Unmapped status codes and connection errors exit with code 1. Success is always 0.
- Auth and health commands handle errors directly in the command function — use the same `body.get("detail") or body.get("message")` pattern, and should also respect JSON mode and semantic exit codes
- `httpx.Client.delete()` does not support `json` kwarg — for DELETE requests with a JSON body, use `client.request("DELETE", url, json=...)` directly (see `inbox.py` remove-tags)

## Output
- Rich output by default via `formatting.py` helpers (`print_table`, `print_detail`)
- `--json` flag outputs raw JSON to stdout for piping/scripting
- `--json` is a **subcommand-level option** on every command (not on the group callback). Use `JSON_OPTION` from `_helpers.py`:
  ```python
  from ac_cli.commands._helpers import JSON_OPTION, set_json_mode

  @app.command()
  def list(ctx: typer.Context, json_output: bool = JSON_OPTION, ...):
      set_json_mode(json_output)
      ...
      if json_output:
          print_json(data)
  ```
- Every command that supports JSON must call `set_json_mode(json_output)` at the start so that `_handle_error()` and `_api_request()` emit JSON errors when `--json` is active
- Usage: `ac crm companies list --json`, `ac health check --json`, `ac whoami --json`

## List Commands & Pagination
- All API list endpoints return a standardized paginated response: `{"data": [...], "total": N, "limit": N, "offset": N, "has_more": bool}`
- List commands should accept `--limit` (default 50) and `--offset` (default 0) options, and always send both as query params
- For endpoints returning paginated responses, extract items via `data.get("data", [])` and show server-reported total in table titles: `f"Title ({data.get('total', '?')} total)"`
- Some legacy endpoints (communications list, thread, recipients) still return raw lists — use `isinstance(data, list)` fallback for those: `items = data if isinstance(data, list) else data.get("data", [])`
- CRM, envoy inbox, and envoy outbox commands all follow the paginated pattern

## Delete Commands
- Always require `--yes` / `-y` flag or interactive `typer.confirm()` prompt
- Use `should_skip_confirm(yes)` instead of `if not yes:` — this also checks the `AC_YES` env var

## Non-Interactive Mode
- `should_skip_confirm(yes_flag)` from `_helpers.py` returns `True` if the `--yes` flag is set OR `AC_YES` env var is `1`, `true`, or `yes`
- All `typer.confirm()` call sites must use this: `if not should_skip_confirm(yes): typer.confirm(...)`
- This allows agents and scripts to set `AC_YES=1` globally instead of passing `--yes` to every destructive command

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
