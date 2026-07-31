# finance-tracker cheatsheet

Every command runs from the project root:

```
cd ~/dev/finance-tracker/finance-tracker
```

`.venv/bin/python` is the project's Python — using it means you never have to
"activate" the venv.

---

## Dashboard

| What | Command |
|------|---------|
| Rebuild `dashboard.html` and open it in a browser | `.venv/bin/python scripts/generate_dashboard.py` |
| Rebuild without opening a browser | `.venv/bin/python scripts/generate_dashboard.py --no-open` |
| Rebuild it from a CSV instead of Plaid | `.venv/bin/python scripts/generate_dashboard.py --from-csv data/transactions.csv` |
| Live dashboard — working Run button + budget saving (localhost) | `.venv/bin/python scripts/serve_dashboard.py` → visit http://localhost:8000 |
| Same, reachable from your phone on home Wi-Fi | `.venv/bin/python scripts/serve_dashboard.py --host 0.0.0.0` → http://<mac-ip>:8000 |

Stop the server with `Ctrl+C`.

`generate_dashboard.py` opens the file automatically; the **Run** button and
saving budget edits to `config/budgets.yaml` only work via `serve_dashboard.py`.

---

## Reports & notifications

| What | Command |
|------|---------|
| Default report + send ntfy push | `.venv/bin/python -m src.main` |
| Report to screen only, no push | `.venv/bin/python -m src.main --no-notify` |
| Incremental "new charges" alert (what the 5 PM job sends) | `.venv/bin/python -m src.main --sync` |

The push goes to your ntfy topic (`NTFY_TOPIC` in `.env`). Add `--no-notify` to
any command below to just print and skip the push.

---

## Date ranges

Add one of these to `python -m src.main`:

| Range | Flag |
|-------|------|
| Today | `--window today` |
| Last 2 days | `--window last_2_days` |
| Last 7 days | `--window last_7_days` |
| Month to date | `--window mtd` |
| Last 30 days | `--window last_30_days` |
| Custom dates | `--start 2026-06-01 --end 2026-06-30` |

Example — month-to-date, print only:

```
.venv/bin/python -m src.main --window mtd --no-notify
```

`--end` defaults to today if you leave it off.

---

## Specific banks / accounts

There's no per-bank flag — which accounts get pulled is controlled by the
`enabled:` toggles in `config/config.yaml`.

| What | How |
|------|-----|
| Pull only certain banks | Set `enabled: true` on the ones you want, `false` on the rest, in `config.yaml` |
| Pull **every** account, ignoring the toggles | add `--pull-all` (e.g. `.venv/bin/python -m src.main --pull-all --no-notify`) |
| See the cards + `account_id`s under each login | `.venv/bin/python scripts/check_accounts.py` |
| Turn an account on/off | Flip `enabled: true`/`false` in `config.yaml` (no code change) |

---

## Adding / managing accounts

| What | Command |
|------|---------|
| Link a new bank (guided wizard) | `.venv/bin/python scripts/add_account.py` |
| Export recent transactions to CSV | `.venv/bin/python scripts/export_transactions.py` |
| One-time backfill (~2 years of history) | `.venv/bin/python scripts/backfill.py` |

---

## Daily automation

| What | Command |
|------|---------|
| Run the full daily job by hand (dashboard + sync alert) | `bash scripts/run_daily.sh` |
| Watch the daily log | `tail -f logs/daily.log` |

The job normally runs itself at 17:00 via launchd. Edit `DASHBOARD_DEST` near
the top of `scripts/run_daily.sh` to auto-copy the dashboard to a cloud folder
that syncs to your phone.

---

## Handy combos

```
# Everything, this month, no push — a quick "where am I" check
.venv/bin/python -m src.main --window mtd --pull-all --no-notify

# Rebuild the dashboard (opens in your browser automatically)
.venv/bin/python scripts/generate_dashboard.py
```
