---
paths:
  - "src/**/*.py"
---

# Code Patterns

## Command Structure
- Each command group is a `typer.Typer()` sub-app registered via `app.add_typer()` in `main.py`
- HTTP client: always use `with get_api_client() as client:` context manager
- IDs are positional `typer.Argument()`, optional fields are `typer.Option(None, ...)`
- Tags: accept comma-separated string on CLI, split to list before API call
- Dates: ISO format strings (`2026-03-15`)

## Error Handling
- Catch `httpx.HTTPStatusError`, print detail, `raise typer.Exit(code=1)`
- Use `_handle_error()` helper in crm.py for consistent error output

## Output
- Rich output by default via `formatting.py` helpers (`print_table`, `print_detail`)
- `--json` flag outputs raw JSON to stdout for piping/scripting
- `--json` is a global option on the crm app group callback, stored in `_json_flag`

## Delete Commands
- Always require `--yes` / `-y` flag or interactive `typer.confirm()` prompt

## Create Commands
- Fetch `organization_id` from `/whoami` before creating resources
