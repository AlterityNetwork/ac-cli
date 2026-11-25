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
- `mock_config` — patches `load_config()` to return valid auth config
- `mock_api` — respx mock router intercepting httpx calls to API base URL
- `invoke` — convenience function combining the two above with a `CliRunner`: `invoke(["crm", "companies", "list"])`
- `table_column` — helper that reads one column from a rendered table

## What to Test Per Command
- **Happy path**: correct API call made, response rendered (table or JSON)
- **`--json` flag**: output is valid JSON (parse with `json.loads`)
- **Error handling with semantic exit codes**: assert the exit code for each error status the command can return. The map is in `code-patterns.md` (Error Handling).
- **JSON error output**: with `--json`, errors return `{"error": true, "status_code": ..., "detail": ...}` — parse with `json.loads` and assert fields
- **`--yes` on delete**: skips confirmation prompt
- **Abort on delete**: `input="n\n"` → exits code 1
- **Update with no fields**: exits code 1, prints "No fields"
- **Create with /whoami**: mock `/whoami` endpoint alongside the create endpoint
- **Org-scoped commands**: test both explicit `--org-id` and auto-resolved from `/whoami`
- **Note on 401 tests**: The httpx client auto-refreshes tokens on 401, triggering a Supabase call. Use 403 instead for auth error tests, or mock the Supabase refresh endpoint. See `test_agent_features.py` for examples.

## Test File Naming
- CRM: `test_crm_<group>.py` (e.g. `test_crm_companies.py`)
- Sequences: `test_sequences_<group>.py` (e.g. `test_sequences_playbooks.py`)
- Workflows: `test_workflows_<group>.py` (e.g. `test_workflows_runs.py`)
- Admin: `test_admin_<group>.py` (e.g. `test_admin_users.py`)
- Other domains: `test_<domain>.py` (e.g. `test_writing_styles.py`, `test_apps.py`, `test_nylas.py`)

## Cross-Cutting Tests
- `test_agent_features.py` — tests for JSON errors, semantic exit codes, `health --json`, `whoami --json`, `AC_YES` env var

## Running
```bash
uv run pytest                              # All tests (coverage floor 90%)
uv run pytest tests/test_crm_deals.py      # Single CRM test file
uv run pytest tests/test_sequences_outbox.py   # Single Sequences test file
uv run pytest tests/test_admin_users.py    # Single Admin test file
uv run pytest tests/test_workflows_runs.py # Single Workflows test file
uv run pytest tests/test_agent_features.py # Agent-friendly features
uv run pytest -k "test_companies"          # By name pattern
```

## Endpoint Audit (CI Gate)
- The audit rules are in `CLAUDE.md` (Running Checks and Critical Rules). Run `uv run python scripts/audit_endpoints.py --strict` before you merge a change to a router or a new command.
