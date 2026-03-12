---
paths:
  - "src/**/*.py"
---

# Code Patterns

## Command Structure
- Each command group is a `typer.Typer()` sub-app registered via `app.add_typer()` in `main.py`
- CRM commands use `_api_request()` helper for HTTP calls with built-in error handling
- Use `_build_body()` helper to construct request bodies from non-None fields (handles tags splitting)
- IDs are positional `typer.Argument()`, optional fields are `typer.Option(None, ...)`
- Tags: accept comma-separated string on CLI, `_build_body` splits to list automatically
- Dates: ISO format strings (`2026-03-15`)

## API Route Prefix
- CRM routes use the `_CRM` constant from `crm/__init__.py` (currently `/api/v1/crm`)
- Envoy routes use the `_ENVOY` constant from `envoy/__init__.py` (currently `/api/v1/envoy`)
- Both domains share `_api_request()` and `_build_body()` from `crm/__init__.py`
- Non-versioned routes (`/whoami`, `/health`) use root paths directly
- No trailing slashes on API paths

## Error Handling
- `_api_request()` catches both `httpx.HTTPStatusError` (API errors) and `httpx.HTTPError` (connection errors)
- `_handle_error()` extracts detail from API error responses and exits with code 1
- Non-CRM/Envoy commands (auth, health) handle errors directly in the command function

## Output
- Rich output by default via `formatting.py` helpers (`print_table`, `print_detail`)
- `--json` flag outputs raw JSON to stdout for piping/scripting
- `--json` is a global option on both the `crm` and `envoy` app group callbacks, passed via `typer.Context`
- Access in subcommands: add `ctx: typer.Context` parameter, read `ctx.obj["json"]`

## Delete Commands
- Always require `--yes` / `-y` flag or interactive `typer.confirm()` prompt

## Create Commands
- Fetch `organization_id` from `/whoami` before creating resources
