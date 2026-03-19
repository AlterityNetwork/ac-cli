# Project Structure

## Layout

- `src/ac_cli/` — source package
  - `main.py` — entry point, registers all command groups
  - `client.py` — authenticated httpx client from stored config
  - `config.py` — load/save `~/.agencycore/config.json`, environment constants (`STAGING_*`, `DEV_*`)
  - `formatting.py` — shared output: `print_table`, `print_detail`, `print_json`
  - `commands/_helpers.py` — shared helpers: `_api_request`, `_build_body`, `_handle_error`
  - `commands/` — standalone modules (`auth.py`, `apps.py`, `writing_styles.py`, `nylas.py`, `hooks.py`, `health.py`) and package-based domains (`crm/`, `envoy/`, `workflows/`, `admin/`, `files/`)
- `tests/` — one test file per command group, named `test_<domain>_<group>.py`
- `scripts/` — `bump.sh` (manual version), `auto-version-tag.sh` (post-commit hook)

## Adding a New Command Group

All command groups follow the same pattern regardless of domain:

1. **Create the module** — either a single file (`commands/<group>.py`) or a package (`commands/<group>/__init__.py` + submodules)
2. **Define the app**: `app = typer.Typer(help="...")` and a prefix constant (e.g. `_FILES = "/api/v1/files"`)
3. **Add `--json` callback**:
   ```python
   @app.callback()
   def callback(ctx: typer.Context, json_output: bool = typer.Option(False, "--json", help="Output raw JSON")) -> None:
       ctx.ensure_object(dict)
       ctx.obj["json"] = json_output
   ```
4. **Write commands** using `_api_request()` from `commands/_helpers.py`, `print_detail`/`print_table`/`print_json` from `formatting.py`
5. **Read JSON flag** in commands via `ctx.obj["json"]`
6. **Register in `main.py`**: `from ac_cli.commands import <group>` + `app.add_typer(<group>.app, name="<group>")`
7. **For sub-groups within a package** (e.g. `files/images.py`): define `<sub>_app = typer.Typer(help="...")`, then import and register in the package's `__init__.py`: `app.add_typer(<sub>_app, name="<sub>")`
8. **Add tests** in `tests/test_<domain>_<group>.py` using the `invoke`, `mock_api`, `tmp_path` fixtures from `conftest.py`
