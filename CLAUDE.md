# ac-cli

Python CLI for AgencyCore. Built with Typer + httpx + Supabase Python client.

## Setup

```bash
pip install -e .
```

## Commands

```
ac login       # Authenticate via Supabase email/password
ac logout      # Clear stored credentials
ac whoami      # Show current user (calls GET /whoami)
ac health check  # Hit GET /health (no auth required)
```

## Config

Credentials stored in `~/.agencycore/config.json` (file mode 0600).

## Stack

- **typer** — CLI framework
- **httpx** — HTTP client
- **supabase** — Auth via `sign_in_with_password`
- **rich** — Terminal formatting

## Running Checks

```bash
# No linter/test setup yet — add as needed
python -m ac_cli.main --help
```
