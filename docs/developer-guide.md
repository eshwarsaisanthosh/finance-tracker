# Developer guide

How the finance-tracker is put together, and how to change it safely.

---

## 1. Mental model

Two zones, two modes.

**Two zones.** `src/` is the *application* — the code that runs on a schedule.
`scripts/` is the *toolbox* — one-off setup and maintenance you run by hand.
If it runs every day, it lives in `src/`; if you run it occasionally from a
terminal, it lives in `scripts/`.

**Two fetch modes.**
- `range` — pull a date window via Plaid `transactions_get`. This is the
  spend-tracker default ("what did I spend over period X").
- `sync` — pull incrementally via Plaid `transactions_sync`, remembering a
  cursor per account. This is the "notify me of new charges" behaviour.

Everything else (processing, summarizing, the dashboard) is mode-agnostic: it
just consumes a list of transactions.

---

## 2. Repository layout

| Path | Role |
|------|------|
| `src/config_loader.py` | Load `.env` + `config.yaml` into one validated dict |
| `src/plaid_client.py` | Build a Plaid API client (one place) |
| `src/dates.py` | Resolve a fetch window into `(start, end)` dates |
| `src/fetcher.py` | Pull transactions (range + sync) across active accounts |
| `src/processor.py` | Clean transactions into a DataFrame, drop non-spend |
| `src/summarizer.py` | Turn the DataFrame into the report text |
| `src/notifier.py` | Send the report via ntfy |
| `src/enrich.py` | Normalize raw Plaid fields (category, merchant, initials) |
| `src/template_dashboard.py` | Render the dashboard model into HTML |
| `src/main.py` | CLI entry point; orchestrates the report pipeline |
| `scripts/*` | Setup + maintenance tools (see below) |
| `scripts/generate_dashboard.py` | Compute the dashboard model, write `dashboard.html` |
| `scripts/run_daily.sh` | The launchd-driven daily job |
| `config/config.yaml` | Accounts, toggles, fetch settings, transfer filters |
| `config/cursors.json` | Per-account sync cursors (auto-managed) |
| `.env` | Secrets: Plaid keys and per-account access tokens |

`scripts/` tools: `generate_link_token`, `exchange_token`, `get_sandbox_token`
(setup); `save_account_map`, `check_accounts` (inspect); `backfill`,
`export_transactions`, `sync_transactions` (data). All use `_bootstrap.py` to
put the project root on `sys.path` so `from src....` works.

---

## 3. The two flows

**Report pipeline** (`python -m src.main`):

```
config_loader → fetcher → processor → summarizer → notifier
   (settings)    (Plaid)   (clean)     (text)       (ntfy)
```

**Dashboard** (`python scripts/generate_dashboard.py`):

```
fetcher → enrich.normalize → compute_model → template.render_html → dashboard.html
 (Plaid)    (clean rows)      (metrics)        (self-contained HTML)
```

Both start from the same `fetcher`. The dashboard adds enrichment (category /
merchant) and a modeling step instead of a text summary.

---

## 4. How a transaction moves through the code

This is the contract to keep in your head. A transaction changes shape at each
hop — know which shape you're holding.

1. **Raw Plaid object** (from `transactions_get` / `transactions_sync`). Has
   `.amount`, `.name`, `.date`, `.account_id`, `.merchant_name`,
   `.personal_finance_category`, `.transaction_id`, and a `.to_dict()`.

2. **Tagged dict** (`fetcher._to_dict`). `to_dict()` plus an added `account`
   key (the friendly name from `config.yaml`) and `date` coerced to an ISO
   string. This is what `fetch_all_transactions` returns.

3. **Normalized row** (`enrich.normalize`, dashboard/export path only):
   `{date, name, amount, account, category, merchant, id}` — `category`
   prettified from `personal_finance_category`, `merchant` from
   `merchant_name` (falls back to `name`).

4. **Cleaned DataFrame** (`processor.filter_expenses`). Drops rows whose `name`
   matches a transfer keyword and any row with `amount <= 0`. Columns are
   whatever keys the input dicts had, so `account` / `category` / `merchant`
   survive if present.

5. **Model dict** (`generate_dashboard.compute_model`) or **report text**
   (`summarizer.generate_summary`), computed from the DataFrame.

Practical rule: `processor` and everything after it expect **dicts** (either
tagged or normalized). Don't pass raw Plaid objects past the fetcher.

---

## 5. Configuration reference

**`.env`** (secrets only):

| Key | Meaning |
|-----|---------|
| `PLAID_CLIENT_ID`, `PLAID_SECRET` | Plaid app credentials (required) |
| `PLAID_HOST` | e.g. `https://production.plaid.com`; wins over `plaid_env` |
| `PLAID_TOKEN_<NAME>` | One access token per bank login |
| `PLAID_ACCESS_TOKEN` | Legacy single token; used if no `accounts` defined |
| `NTFY_TOPIC` | ntfy topic for alerts |

**`config.yaml`**:

| Key | Meaning |
|-----|---------|
| `accounts[].name` | Friendly label, tags each transaction |
| `accounts[].access_token_env` | `.env` var holding this login's token |
| `accounts[].account_ids` | Optional filter to specific cards under a login |
| `accounts[].enabled` | Include this account in pulls |
| `settings.pull_all` | Pull every account, ignoring `enabled` |
| `fetch.mode` | Default mode: `range` or `sync` |
| `fetch.window` | `today` \| `last_2_days` \| `last_7_days` \| `mtd` \| `last_30_days` \| `custom` |
| `fetch.custom` | `start_date` / `end_date` / `lookback_days` (window: custom) |
| `transfer_filters.keywords` | Name substrings that mark non-spend rows |

`load_config()` returns `{plaid, accounts, settings, fetch, app_settings,
transfer_filters}` and raises `RuntimeError` early if credentials or a usable
token are missing.

---

## 6. Core logic explained

**Window resolution (`dates.resolve_window`).** Priority: explicit CLI
`--start/--end` > CLI `--window` > `config.fetch`. Presets are **inclusive of
today**, e.g. `last_7_days` = `[today-6, today]`. `custom` uses `start_date`
if given, else `end_date - (lookback_days-1)`. Guards clamp future `end` to
today and reject `end < start`.

**Amount sign.** Plaid reports outflows as **positive**, inflows negative.
`processor` keeps `amount > 0`, so refunds/payments drop out. If any bank
reports the opposite, spend totals invert — that's the first thing to check on
a new account.

**Transfer filtering.** `processor` drops rows whose `name` contains any
`transfer_filters.keywords` substring (case-insensitive), so card payments and
internal transfers don't count as spending.

**Per-account cursors (`sync` mode).** Each login has its own sync position, so
cursors are stored in `config/cursors.json` keyed by `access_token_env`. One
shared cursor would break with multiple logins.

**Account selection (`fetcher.get_active_accounts`).** Returns all accounts if
`settings.pull_all`, else those with `enabled: true` — and only ones whose
token actually resolved from `.env`.

**Category enrichment (`enrich.prettify_category`).** Reads
`personal_finance_category.primary` (e.g. `FOOD_AND_DRINK`) and turns it into
`Food and drink`. Falls back to the legacy `category` list, then
`Uncategorized`.

---

## 7. Local setup & running

```
cd ~/dev/finance-tracker/finance-tracker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then fill in real values
```

Entry points:

```
python -m src.main                     # report, config default window
python -m src.main --window mtd --no-notify
python -m src.main --sync              # incremental alert mode
python scripts/generate_dashboard.py   # build dashboard.html (live)
python scripts/generate_dashboard.py --from-csv data/transactions.csv
```

---

## 8. Making common changes

**Add a dashboard metric.** Compute it in `compute_model` (add a key to the
returned dict), then render it in `template_dashboard.py`'s JS. Round any
displayed number.

**Add a window preset.** Add a branch in `dates._resolve_preset` and list the
name in `PRESETS`, the `config.yaml` comment, and the `main.py --window` help.

**Change what counts as a transfer.** Edit `transfer_filters.keywords` in
`config.yaml` — no code change.

**Add a field to the report.** Edit `summarizer.generate_summary`.

**Add a new account.** See `docs/adding-an-account.md`.

**Add a new fetch mode.** Add a `fetch_<mode>` function in `fetcher.py` and a
branch in `fetch_all_transactions`; wire a flag in `main.py`.

---

## 9. Testing your changes (no live Plaid needed)

Plaid isn't installable in every environment, and you shouldn't hit the live
API in tests. Two techniques cover most changes:

**Byte-compile + pure-logic tests.** `dates.py`, `processor.py`,
`summarizer.py`, `enrich.py` have no Plaid dependency — test them directly:

```
python -m py_compile src/*.py scripts/*.py
python -c "from src.dates import resolve_window; print(resolve_window({'window':'mtd'}))"
```

**Stub Plaid + mock the client** for `fetcher` / `main` / dashboard. Create a
tiny fake `plaid` package on `PYTHONPATH`, then monkeypatch
`fetcher.get_plaid_client` to return a fake client whose `transactions_get` /
`transactions_sync` return canned data. `compute_model` and
`filter_expenses` can be fed plain dicts with no Plaid at all — prefer that
where possible.

Always verify: run against a fixed `--today` for deterministic dates, assert
totals against an independent recompute, and confirm the dashboard HTML has no
external references (it must stay offline-capable).

---

## 10. Conventions & invariants

- **Secrets only in `.env`.** `config.yaml` names tokens via
  `access_token_env`; it never contains a token.
- **One Plaid token per bank login.** A login can expose several `account_id`s;
  filter with `account_ids`.
- **Dicts after the fetcher.** Never pass raw Plaid objects downstream.
- **Outflows are positive.** Keep this assumption in mind for any money math.
- **The dashboard is offline-capable.** No external CSS/JS/CDN — everything
  inline. Don't add remote assets.
- **Round displayed numbers.** Especially in the dashboard JS.

---

## 11. Known limitations / good first issues

- `scripts/check_accounts.py` reads only the legacy `PLAID_ACCESS_TOKEN`, not
  arbitrary per-account tokens. Make it iterate `get_active_accounts`.
- No automated test suite yet — the recipes in §9 could be packaged under
  `tests/` with `pytest` and the Plaid stub as a fixture.
- Two Plaid pulls happen on the daily run (dashboard + sync). Could share one
  fetch.
- Per-account `account_ids` filtering is client-side; could pass `account_ids`
  to Plaid to filter server-side.
