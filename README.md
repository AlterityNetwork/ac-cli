# AgencyCore CLI

Command-line interface for [AgencyCore](https://agencycore.dev) — manage your CRM, outreach sequences, and pipeline from the terminal.

## Install

```bash
pip install agencycore-cli
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install agencycore-cli
```

Requires Python 3.10+.

## Quick Start

```bash
# Log in (connects to AgencyCore staging by default)
ac login

# Use --dev for local development
ac login --dev

# Check your identity
ac whoami

# Check API health
ac health check
```

## CRM Commands

```bash
# Companies
ac crm companies list
ac crm companies get <id>
ac crm companies create --name "Acme Corp" --industry Technology

# People (Contacts)
ac crm people list
ac crm people create --email jane@acme.com --full-name "Jane Smith"

# Deals
ac crm deals list
ac crm deals create --name "Enterprise Deal" --stage qualified --amount 50000
ac crm deals move <id> --stage negotiation

# Activities
ac crm activities list --status pending
ac crm activities create --type call --title "Follow up" --due-date 2026-03-20

# Communications
ac crm comms unread
ac crm comms draft-email --contact-id <id> --subject "Hello" --content "..."

# Search & Dashboard
ac crm search "acme"
ac crm dashboard --period 30

# Lists & Import
ac crm lists list
ac crm import preview --file contacts.json
```

## Envoy (Outreach)

```bash
ac envoy sequences list
ac envoy outbox pending
ac envoy dashboard
```

## Output Modes

All commands support rich table output (default) or JSON for scripting:

```bash
ac crm deals list                          # Pretty tables
ac crm --json deals list                   # Raw JSON
ac crm --json deals list | jq '.[].name'   # Pipe to jq
```

## Development

```bash
git clone https://github.com/AlterityNetwork/ac-cli.git
cd ac-cli
uv sync --all-extras
uv run pytest
```

## License

MIT
