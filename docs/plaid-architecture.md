# How Plaid works (and how this app uses it)

A practical map of Plaid's model, the keys involved, the connection handshake,
and how data flows — tied to the exact scripts in this repo.

---

## 1. The players

| Player | What it is | Where it lives |
|--------|-----------|----------------|
| Your code | Creates tokens, pulls data | your Mac (`src/`, `scripts/`) |
| Plaid Link | A browser widget the user logs into their bank through | `index.html` |
| Plaid API | Plaid's servers | `https://<env>.plaid.com` |
| The Item | One bank *login* Plaid holds credentials for | Plaid's side, referenced by `item_id` |
| Accounts | The individual accounts/cards under an Item | referenced by `account_id` |

The key idea: **you never see the user's bank password.** The user types it
into Plaid Link (Plaid's widget), Plaid stores the connection as an *Item*, and
hands your app a token that represents that Item.

---

## 2. The keys and tokens

| Key | Secret? | Lifetime | Purpose |
|-----|---------|----------|---------|
| `client_id` | Yes | permanent | Identifies your Plaid app |
| `secret` | Yes | permanent | Authenticates your app (per environment) |
| `link_token` | No (short-lived) | ~hours | Boots up a Plaid Link session |
| `public_token` | No (very short) | ~30 min | Handed back by Link on success; single use |
| `access_token` | **Yes** | permanent* | Used for every data call for that Item |
| `item_id` | No | permanent | Identifies the Item (the login) |
| `account_id` | No | permanent | Identifies one account under an Item |
| `cursor` | No | until superseded | Marks your position in the sync stream |

\* The `access_token` doesn't expire on its own, but can be invalidated
(re-auth needed, item removed, credentials changed).

Why so many tokens? Each has one job and a different trust level. `link_token`
and `public_token` are throwaway handoff tokens that briefly bridge browser and
server; the `access_token` is the durable secret. This separation means the
long-lived secret is only ever created server-side, never exposed in the
browser.

---

## 3. The handshake (one-time, per bank login)

```
 STEP           YOUR CODE                        PLAID              SCRIPT
 ────────────────────────────────────────────────────────────────────────
 1  create   client_id+secret  ───────────────►  /link/token/create
             ◄─────────────────────────────────  link_token         generate_link_token.py

 2  launch   link_token ──► Plaid Link (browser) ──► user logs into bank
                                                                     index.html

 3  success  Plaid Link ◄──────────────────────  connection made
             ◄─────────────────────────────────  public_token       (browser alert)

 4  exchange public_token  ─────────────────────► /item/public_token/exchange
             ◄─────────────────────────────────  access_token + item_id
                                                                     exchange_token.py

 5  store    access_token ──► .env as PLAID_TOKEN_<NAME>             (you paste it)
```

After step 5 the login is permanently connected — you never repeat steps 1–4
for that bank unless the connection breaks and needs re-auth.

Sandbox shortcut: `get_sandbox_token.py` fakes steps 1–4 against a test bank so
you get an `access_token` without a real login.

---

## 4. Pulling data (every run)

Once you hold an `access_token`, all data calls are just: your code +
`client_id` + `secret` + `access_token` → a Plaid endpoint.

| Endpoint | What it returns | Used by |
|----------|-----------------|---------|
| `/accounts/get` | The accounts under the Item | `check_accounts.py`, `save_account_map.py` |
| `/transactions/get` | Transactions in a **date range** | `fetch_range`, `backfill.py`, `export_transactions.py` |
| `/transactions/sync` | Transactions **since a cursor** | `fetch_sync`, `sync_transactions.py` |

**Range (`/transactions/get`).** You ask for `start_date`..`end_date` and page
through with `count`/`offset`. Simple; good for "show me this period."

**Sync (`/transactions/sync`).** Plaid returns `added`, `modified`, `removed`
plus `next_cursor` and `has_more`. You loop until `has_more` is false, then save
`next_cursor`. Next run you send that cursor and get only what changed. This app
stores one cursor per Item in `config/cursors.json` (keyed by
`access_token_env`) because each login has its own independent stream.

This app **polls** on a schedule. Production apps often instead register a
**webhook** and let Plaid notify them (`SYNC_UPDATES_AVAILABLE`) when new
transactions arrive — not used here, but that's how "real-time" is done.

---

## 5. The Item model (why the config looks the way it does)

```
Item (one bank login, one access_token)
 ├── account_id  ── "Delta SkyMiles Platinum"
 └── account_id  ── "Corporate Card"
```

One `access_token` covers **all** accounts under that login. That's why:

- Each `config.yaml` account entry names an `access_token_env` (the Item's
  token), and
- `account_ids` optionally narrows one entry to specific cards under that Item.

Two cards at *different* banks = two Items = two `access_token`s. Two cards at
the *same* bank = one Item = one `access_token`, split by `account_id`.

---

## 6. Environments

| Environment | Host | Data |
|-------------|------|------|
| Sandbox | `https://sandbox.plaid.com` | fake test banks/credentials |
| Development | `https://development.plaid.com` | real banks, limited Items |
| Production | `https://production.plaid.com` | real banks, live |

The `secret` and every `access_token` are **environment-specific** — a
production token won't work against the sandbox host and vice-versa. This app
resolves the host from `PLAID_HOST` (falling back to `app_settings.plaid_env`).

---

## 7. Security model

- `client_id`, `secret`, and every `access_token` are secrets → `.env` only,
  which is gitignored. Never in `config.yaml`, never in the browser.
- `link_token` / `public_token` are safe to pass through the browser: they're
  short-lived and useless without your server-side `secret` to exchange them.
- If an `access_token` leaks, rotate it in the Plaid dashboard (remove the Item
  and reconnect) — the same as revoking access.

---

## 8. Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `INVALID_API_KEYS` | wrong `client_id`/`secret` or wrong environment | check `.env` + `PLAID_HOST` |
| `link_token` errors in Link | it expired | regenerate (step 1), redo promptly |
| `public_token` exchange fails | it expired (~30 min) or was reused | rerun Link for a fresh one |
| `ITEM_LOGIN_REQUIRED` | bank needs re-auth (password/MFA changed) | run Link again for that Item to refresh the token |
| `PRODUCTS_NOT_SUPPORTED` | `transactions` not enabled for the Item | enable the product / re-link |
| Empty results in sync | you're caught up (cursor at head) | expected; use range mode or delete the cursor |

---

## 9. Concept → code map

| Plaid concept | This repo |
|---------------|-----------|
| create `link_token` | `scripts/generate_link_token.py` |
| Plaid Link UI | `index.html` |
| exchange `public_token` | `scripts/exchange_token.py` |
| store `access_token` | `.env` (`PLAID_TOKEN_<NAME>`) |
| build API client | `src/plaid_client.py` |
| list accounts | `scripts/check_accounts.py`, `save_account_map.py` |
| range pull | `src/fetcher.py::fetch_range` |
| sync pull + cursor | `src/fetcher.py::fetch_sync`, `config/cursors.json` |
| Item → accounts mapping | `config.yaml` accounts + `account_ids` |
