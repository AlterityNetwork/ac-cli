# Project Structure

## Layout

- `src/ac_cli/` — source package
  - `main.py` — entry point, registers all command groups
  - `client.py` — authenticated httpx client from stored config
  - `config.py` — multi-env config (`~/.agencycore/config.json`), environment constants (`PROD_*`, `STAGING_*`, `DEV_*`), `ENVIRONMENTS` registry, migration from legacy flat format
  - `formatting.py` — shared output: `print_table`, `print_detail`, `print_json`
  - `commands/_helpers.py` — shared helpers: `_api_request`, `_build_body`, `_get_org_id`, `_handle_error`, `set_json_mode`, `should_skip_confirm`, `_EXIT_CODES`
  - `commands/` — standalone modules (`auth.py`, `env.py`, `apps.py`, `writing_styles.py`, `nylas.py`, `hooks.py`, `health.py`, `legal_documents.py`, `tos.py`, `marketplace.py`, `network.py`, `managed_onboarding.py`) and package-based domains (`crm/`, `envoy/`, `workflows/`, `admin/`, `files/`)
- `tests/` — one test file per command group, named `test_<domain>_<group>.py`
- `scripts/` — `bump.sh` (manual version), `auto-version-tag.sh` (post-commit hook)

## Adding a New Command Group

All command groups follow the same pattern regardless of domain:

1. **Create the module** — either a single file (`commands/<group>.py`) or a package (`commands/<group>/__init__.py` + submodules)
2. **Define the app**: `app = typer.Typer(help="...")` and a prefix constant (e.g. `_FILES = "/api/v1/files"`)
3. **Add a simple callback** (for context initialization only):
   ```python
   @app.callback()
   def callback(ctx: typer.Context) -> None:
       ctx.ensure_object(dict)
   ```
4. **Write commands** using `_api_request()` from `commands/_helpers.py`, `print_detail`/`print_table`/`print_json` from `formatting.py`
5. **Add `--json` to each command** using the shared `JSON_OPTION` constant:
   ```python
   from ac_cli.commands._helpers import JSON_OPTION, set_json_mode

   @app.command()
   def list(ctx: typer.Context, json_output: bool = JSON_OPTION, ...):
       set_json_mode(json_output)
       ...
       if json_output:
           print_json(data)
   ```
   The `set_json_mode()` call is **required** — it enables structured JSON error output and is what makes errors agent-friendly when `--json` is active.
6. **For delete/destructive commands**, use `should_skip_confirm(yes)` instead of `if not yes:`:
   ```python
   from ac_cli.commands._helpers import should_skip_confirm

   yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
   ...
   if not should_skip_confirm(yes):
       typer.confirm("Delete this resource?", abort=True)
   ```
7. **Register in `main.py`**: `from ac_cli.commands import <group>` + `app.add_typer(<group>.app, name="<group>")`
8. **For sub-groups within a package** (e.g. `files/images.py`): define `<sub>_app = typer.Typer(help="...")`, then import and register in the package's `__init__.py`: `app.add_typer(<sub>_app, name="<sub>")`
9. **Add tests** in `tests/test_<domain>_<group>.py` using the `invoke`, `mock_api`, `tmp_path` fixtures from `conftest.py`
