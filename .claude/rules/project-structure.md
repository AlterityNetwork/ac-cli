# Project Structure

```
ac-cli/
├── src/ac_cli/
│   ├── main.py              # Entry point, registers all sub-apps
│   ├── client.py            # Authenticated httpx client from stored config
│   ├── config.py            # Load/save ~/.agencycore/config.json
│   ├── formatting.py        # Shared output: print_table, print_detail, print_json
│   └── commands/
│       ├── auth.py           # login, logout, whoami
│       ├── health.py         # health check (no auth)
│       └── crm.py            # All CRM subcommands (~650 lines)
├── tests/
│   ├── conftest.py           # Shared fixtures (mock_api, mock_config, invoke)
│   ├── test_formatting.py
│   ├── test_crm_search.py
│   ├── test_crm_companies.py
│   ├── test_crm_people.py
│   ├── test_crm_deals.py
│   ├── test_crm_activities.py
│   ├── test_crm_dashboard.py
│   └── test_crm_lists.py
├── pyproject.toml
└── uv.lock
```

## Adding New Command Groups
1. Create `src/ac_cli/commands/<group>.py` with `app = typer.Typer(help="...")`
2. Import and register in `main.py`: `app.add_typer(<group>.app, name="<group>")`
3. If crm.py exceeds ~800 lines, split into `commands/crm/` package

## API Endpoints
All CRM commands hit the ac-python-api at `/crm/*`. The API base URL is stored in `~/.agencycore/config.json` (set during `ac login`).
