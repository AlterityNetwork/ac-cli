# Project Structure

```
ac-cli/
├── src/ac_cli/
│   ├── main.py              # Entry point, registers all sub-apps
│   ├── client.py            # Authenticated httpx client from stored config
│   ├── config.py            # Load/save ~/.agencycore/config.json, DEFAULT_API_URL
│   ├── formatting.py        # Shared output: print_table, print_detail, print_json
│   └── commands/
│       ├── auth.py           # login, logout, whoami
│       ├── health.py         # health check (no auth)
│       └── crm/              # CRM subcommands (package)
│           ├── __init__.py    # app, shared helpers (_CRM, _api_request, _build_body, _handle_error), search, dashboard
│           ├── companies.py   # companies_app: list, get, create, update, delete
│           ├── people.py      # people_app: list, get, create, update, delete
│           ├── deals.py       # deals_app: list, get, create, update, move, delete
│           ├── activities.py  # activities_app: list, get, create, update, complete, delete
│           ├── communications.py  # communications_app: list, get, thread, unread, mark-read, delete, delete-thread
│           └── lists.py       # lists_app: list, get, create, update, members, add-member, remove-member, delete
├── tests/
│   ├── conftest.py           # Shared fixtures (mock_api, mock_config, invoke)
│   ├── test_formatting.py
│   ├── test_crm_search.py
│   ├── test_crm_companies.py
│   ├── test_crm_people.py
│   ├── test_crm_deals.py
│   ├── test_crm_activities.py
│   ├── test_crm_communications.py
│   ├── test_crm_dashboard.py
│   ├── test_crm_lists.py
│   └── test_token_refresh.py
├── pyproject.toml
└── uv.lock
```

## Adding New CRM Subcommand Groups
1. Create `src/ac_cli/commands/crm/<group>.py` with `<group>_app = typer.Typer(help="...")`
2. Import shared helpers: `from ac_cli.commands.crm import _CRM, _api_request, _build_body`
3. Add `ctx: typer.Context` as first parameter to commands that need `--json` output
4. Use `_api_request("get", ...)` for API calls and `_build_body(...)` for request bodies
5. Read JSON flag via `ctx.obj["json"]`
6. Register in `crm/__init__.py`: import the app and call `app.add_typer(<group>_app, name="<group>")`

## Adding Non-CRM Command Groups
1. Create `src/ac_cli/commands/<group>.py` with `app = typer.Typer(help="...")`
2. Import and register in `main.py`: `app.add_typer(<group>.app, name="<group>")`

## API Endpoints
All CRM commands hit the ac-python-api at `/api/v1/crm/*`. The `_CRM` constant in `crm/__init__.py` holds this prefix. The API base URL (default `http://localhost:8008`) is stored in `~/.agencycore/config.json` (set during `ac login`). The default URL constant lives in `config.py` as `DEFAULT_API_URL`.
