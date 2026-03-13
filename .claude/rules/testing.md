---
paths:
  - "tests/**/*.py"
---

# Testing

## Stack
- **pytest** for test runner
- **respx** for mocking httpx requests (cleaner than pytest-httpx for sync client)
- **typer.testing.CliRunner** for invoking CLI commands

## Fixtures (in `tests/conftest.py`)
- `cli_runner` — CliRunner instance
- `mock_config` — patches `load_config()` to return valid auth config
- `mock_api` — respx mock router intercepting httpx calls to API base URL
- `invoke` — convenience function combining all three: `invoke(["crm", "companies", "list"])`

## What to Test Per Command
- **Happy path**: correct API call made, response rendered (table or JSON)
- **`--json` flag**: output is valid JSON (parse with `json.loads`)
- **Error handling**: API returns 404/422/500 → CLI prints error, exits code 1
- **`--yes` on delete**: skips confirmation prompt
- **Abort on delete**: `input="n\n"` → exits code 1
- **Update with no fields**: exits code 1, prints "No fields"
- **Create with /whoami**: mock `/whoami` endpoint alongside the create endpoint
- **Org-scoped commands**: test both explicit `--org-id` and auto-resolved from `/whoami`

## Test File Naming
- CRM: `test_crm_<group>.py` (e.g. `test_crm_companies.py`)
- Envoy: `test_envoy_<group>.py` (e.g. `test_envoy_playbooks.py`)
- Workflows: `test_workflows_<group>.py` (e.g. `test_workflows_runs.py`)
- Admin: `test_admin_<group>.py` (e.g. `test_admin_users.py`)
- Other domains: `test_<domain>.py` (e.g. `test_writing_styles.py`, `test_apps.py`, `test_nylas.py`, `test_hooks.py`)

## Running
```bash
uv run pytest                              # All tests (~334 tests)
uv run pytest tests/test_crm_deals.py      # Single CRM test file
uv run pytest tests/test_envoy_outbox.py   # Single Envoy test file
uv run pytest tests/test_admin_users.py    # Single Admin test file
uv run pytest tests/test_workflows_runs.py # Single Workflows test file
uv run pytest -k "test_companies"          # By name pattern
```
