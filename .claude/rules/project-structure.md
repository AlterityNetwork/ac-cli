# Project Structure

```
ac-cli/
├── src/ac_cli/
│   ├── main.py              # Entry point, registers all sub-apps
│   ├── client.py            # Authenticated httpx client from stored config
│   ├── config.py            # Load/save ~/.agencycore/config.json, environment constants (STAGING_*, DEV_*)
│   ├── formatting.py        # Shared output: print_table, print_detail, print_json
│   └── commands/
│       ├── auth.py           # login, logout, whoami
│       ├── health.py         # health check (no auth)
│       ├── crm/              # CRM subcommands (package)
│       │   ├── __init__.py    # app, shared helpers (_CRM, _api_request, _build_body, _handle_error), search, dashboard
│       │   ├── companies.py   # companies_app: list, get, create, update, delete
│       │   ├── people.py      # people_app: list, get, create, update, delete
│       │   ├── deals.py       # deals_app: list, get, create, update, move, order, delete
│       │   ├── activities.py  # activities_app: list, get, create, update, complete, delete
│       │   ├── communications.py  # communications_app: list, get, thread, unread, mark-read, delete, delete-thread, update, archive, unarchive, contact-by-email, resolve-contact, draft-email, generate-draft, unread-thread-ids
│       │   ├── lists.py       # lists_app: list, get, create, update, members, add-member, remove-member, delete
│       │   └── imports.py     # imports_app: preview, commit
│       └── envoy/            # Envoy outreach subcommands (package)
│           ├── __init__.py    # app, _ENVOY prefix, envoy_callback, registers sub-apps
│           ├── sequences.py   # sequences_app: list, get, create, update, delete, launch, pause, resume
│           ├── steps.py       # steps_app: create, update, delete, reorder, stats
│           ├── recipients.py  # recipients_app: list, add, remove
│           ├── outbox.py      # outbox_app: pending, sent, step-drafts, update-draft, approve, reject, regenerate
│           └── dashboard.py   # dashboard_command (standalone command, not sub-app)
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
│   ├── test_crm_imports.py
│   ├── test_envoy_sequences.py
│   ├── test_envoy_steps.py
│   ├── test_envoy_recipients.py
│   ├── test_envoy_outbox.py
│   ├── test_envoy_dashboard.py
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

## Adding Envoy Subcommand Groups
1. Create `src/ac_cli/commands/envoy/<group>.py` with `<group>_app = typer.Typer(help="...")`
2. Import shared helpers: `from ac_cli.commands.crm import _api_request, _build_body`
3. Import envoy prefix: `from ac_cli.commands.envoy import _ENVOY`
4. Add `ctx: typer.Context` as first parameter to commands that need `--json` output
5. Read JSON flag via `ctx.obj["json"]`
6. Register in `envoy/__init__.py`: import the app and call `app.add_typer(<group>_app, name="<group>")`

## Adding Non-CRM/Envoy Command Groups
1. Create `src/ac_cli/commands/<group>.py` (or package) with `app = typer.Typer(help="...")`
2. Import and register in `main.py`: `app.add_typer(<group>.app, name="<group>")`

## API Endpoints
- CRM commands hit `/api/v1/crm/*` — the `_CRM` constant in `crm/__init__.py` holds this prefix
- Envoy commands hit `/api/v1/envoy/*` — the `_ENVOY` constant in `envoy/__init__.py` holds this prefix
- Both share `_api_request()` and `_build_body()` helpers from `crm/__init__.py`
- The API base URL is stored in `~/.agencycore/config.json` (set during `ac login`). Environment constants live in `config.py`: `STAGING_*` (default) and `DEV_*` (used with `ac login --dev`).
