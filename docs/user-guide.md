# Finance Tracker — User Guide

A personal spend tracker that pulls transactions from your bank accounts via
Plaid, sends a daily alert via ntfy, and generates a local HTML dashboard.

---

## 1. Overview

The tracker has two main outputs:

- **Daily report** — a text summary of new charges, sent to your phone via [ntfy](https://ntfy.sh). Runs automatically at 5 PM.
- **Dashboard** — a self-contained `dashboard.html` file you can open in any browser (or sync to your phone via iCloud/Dropbox/etc.).

Data flow:

```
Plaid API → fetch transactions → filter non-spend → summarize → ntfy alert
                                                              → dashboard.html
```

Everything runs locally on your Mac. Your bank credentials never pass through
this app — Plaid handles authentication on their side.

---

## 2. Prerequisites & Installation

**Requirements**

- macOS (the automation uses launchd)
- Python 3.11 or later
- A [Plaid](https://plaid.com) account (free Developer tier is sufficient)
- An [ntfy](https://ntfy.sh) topic for push notifications

**Install**

```bash
cd ~/dev/finance-tracker/finance-tracker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

---

## 3. Configuration

Configuration is split across two files: `.env` for secrets and `config.yaml`
for everything else.

### `.env` — secrets

Create this file at the project root (it's gitignored):

```env
# Plaid credentials (from your Plaid dashboard)
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_HOST=https://production.plaid.com   # or https://sandbox.plaid.com

# One line per bank login — see Section 4 for how to get these
PLAID_ACCESS_TOKEN=access-production-xxxxxxxx

# ntfy topic for push alerts
NTFY_TOPIC=your-topic-name
```

### `config.yaml` — accounts and behaviour

Key sections:

**`accounts`** — list of cards to track. Each entry names an `access_token_env`
(the `.env` variable holding that login's token) and can optionally scope to
specific card IDs under that login:

```yaml
accounts:
  - name: "Delta SkyMiles Platinum"
    access_token_env: PLAID_ACCESS_TOKEN
    account_ids: ["Zz8q..."]   # omit to include all cards under this login
    enabled: true
```

**`fetch`** — controls what window of transactions to pull:

```yaml
fetch:
  mode: range        # range (date window) or sync (new charges only)
  window: last_7_days
```

**`transfer_filters`** — keywords used to drop payment/transfer rows from the
report (e.g. "PAYMENT TO", "TRANSFER"). Add any patterns your bank uses.

---

## 4. Connecting a Bank Account

Each bank login is a one-time setup. Do this in a single sitting — the tokens
are short-lived.

**Step 1 — Generate a link token**

```bash
.venv/bin/python scripts/generate_link_token.py
```

Copy the printed `link-` token.

**Step 2 — Connect the bank**

1. Open `index.html`, replace the `linkToken` value (line ~10) with your token, save.
2. Open `index.html` in your browser.
3. Log into the bank in the popup.
4. On "Success!", copy the `public_token` from the alert.

**Step 3 — Exchange for an access token**

```bash
.venv/bin/python scripts/exchange_token.py
```

Paste the `public_token` when prompted. Copy the printed `access-` token.

**Step 4 — Save the token**

Add to `.env`:

```env
PLAID_TOKEN_CHASE=access-production-xxxxxxxx
```

**Step 5 — Register the account**

Add to `config.yaml` under `accounts:`:

```yaml
  - name: "Chase Freedom"
    access_token_env: PLAID_TOKEN_CHASE
    enabled: true
```

**Step 6 — Test it**

```bash
.venv/bin/python -m src.main --window today --no-notify
```

You should see a line like `[Chase Freedom] N transactions`.

---

## 5. Running the Code

All commands run from the project root with the venv:

```bash
cd ~/dev/finance-tracker/finance-tracker
```

### At a glance — the ways to run it

| I want to… | Command | Details |
|------------|---------|---------|
| Send / preview the spend report | `.venv/bin/python -m src.main …` | §5 below |
| Build the dashboard as an HTML file | `.venv/bin/python scripts/generate_dashboard.py` | §6 |
| Open the dashboard as a live web app (Refresh button) | `.venv/bin/python scripts/serve_dashboard.py` | §6 |
| Run everything automatically at 5 PM | launchd job (`run_daily.sh`) | §7 |
| One-time setup / maintenance | scripts in `scripts/` | §5 utility scripts |

Tip: run `source .venv/bin/activate` once per terminal session and you can drop
the `.venv/bin/` prefix (just `python …`).

### Run the spend report

**Basic usage**

```bash
# Use whatever window is set in config.yaml (default: last_7_days)
.venv/bin/python -m src.main

# Override the window
.venv/bin/python -m src.main --window mtd          # month-to-date
.venv/bin/python -m src.main --window today
.venv/bin/python -m src.main --window last_30_days

# Custom date range
.venv/bin/python -m src.main --start 2026-06-01 --end 2026-06-30

# New charges only (sync mode)
.venv/bin/python -m src.main --sync

# Pull every account regardless of 'enabled' toggles
.venv/bin/python -m src.main --pull-all
```

**Useful flags**

| Flag | Effect |
|------|--------|
| `--no-notify` | Print the report; skip the ntfy alert |
| `--pull-all` | Override `enabled: false` on any account |
| `--sync` | Incremental mode — only new charges since last run |
| `--window <preset>` | `today`, `last_2_days`, `last_7_days`, `mtd`, `last_30_days`, `custom` |
| `--start` / `--end` | Explicit date range (YYYY-MM-DD) |

### Setup & utility scripts

Occasional-use tools in `scripts/`, run with `.venv/bin/python scripts/<name>.py`:

| Script | Purpose | When you'd use it |
|--------|---------|-------------------|
| `generate_link_token.py` | Create a Plaid Link token | Connecting a bank (§4) |
| `exchange_token.py` | Exchange a public token for an access token | Connecting a bank (§4) |
| `get_sandbox_token.py` | Mint a sandbox test token (no real bank) | Trying it without live data |
| `check_accounts.py` | List account names + IDs under a login | Finding `account_id`s (§8) |
| `save_account_map.py` | Save an account_id → name map into `config/` | Optional labelling |
| `export_transactions.py` | Export enriched transactions to `data/transactions.csv` | Archiving / CSV-mode dashboard |
| `backfill.py` | Pull up to ~2 years of history | One-time historical import |
| `sync_transactions.py` | Run the incremental sync and print the count | Debugging sync mode |

---

## 6. The Dashboard

The dashboard is a self-contained HTML file with charts and a transaction table
covering roughly the last 100 days.

**Generate it**

```bash
.venv/bin/python scripts/generate_dashboard.py
```

This writes `dashboard.html` to the project root. Open it in any browser.

Options:

| Flag | Effect |
|------|--------|
| `--from-csv <path>` | Build from an exported CSV instead of a live Plaid pull |
| `--out <path>` | Write the HTML somewhere other than `dashboard.html` |
| `--days <n>` | Days of history to pull (live mode; default ~110) |
| `--today <YYYY-MM-DD>` | Override "today" (for testing) |

**Serve it as a live web app (working Refresh button)**

Instead of a static file, run the dashboard as a small local server. Its
Refresh button pulls fresh data from Plaid on demand and re-renders in place —
no waiting for the daily job:

```bash
.venv/bin/python scripts/serve_dashboard.py          # http://127.0.0.1:8000 (this Mac only)
.venv/bin/python scripts/serve_dashboard.py --host 0.0.0.0        # reachable on home Wi-Fi
.venv/bin/python scripts/serve_dashboard.py --from-csv data/transactions.csv   # no Plaid
```

| Flag | Effect |
|------|--------|
| `--host 0.0.0.0` | Expose on your LAN; visit `http://<mac-ip>:8000` from your phone |
| `--port <n>` | Serve on a different port (default 8000) |
| `--from-csv <path>` | Serve from a CSV (no live Plaid calls) |

Home network only — reaching it from anywhere needs a tunnel plus a login
(it's your bank data). The same `dashboard.html` works both ways: served, the
Refresh button does a live pull; opened as a static file, it falls back to a
plain reload.

**View on your phone (static file)**

Edit `scripts/run_daily.sh` and set `DASHBOARD_DEST` to a folder that syncs to
your phone (iCloud Drive, Dropbox, OneDrive, or Google Drive). The daily job
will copy the file there automatically after each refresh.

```bash
# Example: iCloud Drive
DASHBOARD_DEST="$HOME/Library/Mobile Documents/com~apple~CloudDocs/finance"
```

---

## 7. Daily Automation

The tracker runs automatically at **5:00 PM every day** via a macOS launchd
job. Each run: rebuilds the dashboard, sends the sync alert, and (optionally)
copies the dashboard to your cloud folder.

**Install the job**

```bash
cp deploy/com.eswarbandaru.finance-tracker.daily.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.eswarbandaru.finance-tracker.daily.plist
```

**Uninstall / disable**

```bash
launchctl unload ~/Library/LaunchAgents/com.eswarbandaru.finance-tracker.daily.plist
```

**Logs**

| File | Contents |
|------|----------|
| `logs/daily.log` | Step-by-step output from each daily run |
| `logs/launchd.out.log` | stdout captured by launchd |
| `logs/launchd.err.log` | stderr captured by launchd |

---

## 8. Managing Accounts

**Enable / disable an account** — flip `enabled` in `config.yaml`. No code
changes needed:

```yaml
  - name: "Corporate Card"
    access_token_env: PLAID_ACCESS_TOKEN
    enabled: false   # won't be pulled
```

Set `settings.pull_all: true` to override all toggles and pull everything.

**Multiple cards under one login** — if one bank login exposes several cards,
use `account_ids` to assign each card to its own named entry:

```yaml
  - name: "Chase Sapphire"
    access_token_env: PLAID_TOKEN_CHASE
    account_ids: ["<account_id_1>"]
    enabled: true

  - name: "Chase Freedom"
    access_token_env: PLAID_TOKEN_CHASE
    account_ids: ["<account_id_2>"]
    enabled: true
```

To find the `account_id` values for a login, run:

```bash
.venv/bin/python scripts/check_accounts.py
```

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Nothing pulled for an account | `access_token_env` in `config.yaml` doesn't match the variable name in `.env` | Check for typos — it must match exactly |
| `link_token` error in browser | Token expired (they're short-lived) | Regenerate with `generate_link_token.py` and redo immediately |
| `public_token` exchange fails | Token expired (~30 min) or already used | Run through `index.html` again for a fresh one |
| Wrong environment error | Token environment doesn't match `PLAID_HOST` | Make sure `PLAID_HOST` in `.env` matches the environment your tokens were issued in |
| `ITEM_LOGIN_REQUIRED` | Bank credentials changed or MFA required | Re-run the Plaid Link flow for that account (steps 1–5 in Section 4) |
| Sync returns nothing | Already caught up — no new transactions | Expected behaviour; use `--window` range mode to see recent history |
| Daily job not running | launchd job not loaded | Run the `launchctl load` command in Section 7 |
| Report includes transfers/payments | Keyword not in `transfer_filters` | Add the transaction description keyword to `config.yaml` under `transfer_filters.keywords` |
