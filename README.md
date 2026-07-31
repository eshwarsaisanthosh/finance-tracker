# finance-tracker

A personal spend tracker that pulls transactions from bank accounts via
[Plaid](https://plaid.com), sends a daily push alert via [ntfy](https://ntfy.sh),
and generates a self-contained HTML dashboard.

Everything runs locally on your Mac. Your bank credentials never pass through
this app — Plaid handles authentication on their side.

## Quick links

- **[User guide](docs/user-guide.md)** — setup, configuration, running the app, the dashboard, daily automation
- **[Adding an account](docs/adding-an-account.md)** — step-by-step: link a new bank
- **[How Plaid works](docs/plaid-architecture.md)** — token model, handshake, data flow
- **[Developer guide](docs/developer-guide.md)** — repo layout, code walkthrough, making changes, testing

## At a glance

```
Plaid API → fetch transactions → filter non-spend → summarize → ntfy alert
                                                             → dashboard.html
```

## Requirements

- macOS (the automation uses launchd)
- Python 3.11+
- A free [Plaid Developer account](https://dashboard.plaid.com/signup)
- An [ntfy](https://ntfy.sh) topic for push notifications

## Install

```bash
cd ~/dev/finance-tracker/finance-tracker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env    # fill in your Plaid credentials and ntfy topic
```

### Your config stays yours

Personal settings live in files that are **not** committed, so pushing/pulling
code never touches them and never publishes your accounts:

| Committed template | Your local copy (gitignored) | Holds |
|--------------------|------------------------------|-------|
| `.env.example` | `.env` | Plaid + ntfy secrets |
| `config/config.example.yaml` | `config/config.yaml` | your accounts + fetch settings |
| `config/budgets.example.yaml` | `config/budgets.yaml` | your budget targets |
| `config/account_map.example.json` | `config/account_map.json` | account_id → friendly names |

On first run the app auto-creates `config.yaml` and `budgets.yaml` from their
`.example` templates if they're missing (it never overwrites an existing one).
Or copy them yourself: `cp config/config.example.yaml config/config.yaml`.

See the [user guide](docs/user-guide.md) for full setup instructions, including
[how to obtain your Plaid API keys](docs/user-guide.md#3-obtaining-plaid-api-keys).
