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

## Running
```bash
uv run pytest                          # All tests
uv run pytest tests/test_crm_deals.py  # Single file
uv run pytest -k "test_companies"      # By name pattern
```
