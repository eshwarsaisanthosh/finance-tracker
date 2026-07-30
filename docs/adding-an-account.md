# Adding a new account

## The easy way: one command

```
cd ~/dev/finance-tracker/finance-tracker
.venv/bin/python scripts/add_account.py
```

The wizard runs the whole flow for you: it generates the link token, injects it
into `index.html` and opens your browser, exchanges the `public_token` you copy
back, lets you pick which card(s) under the login to track, then writes the
token to `.env` and the account entry to `config.yaml` — and offers a test run
at the end. Your `.env` and `config.yaml` are backed up (timestamped `.bak`)
before any edit.

You only do three things by hand: log into your bank in the popup, paste the
`public_token` when prompted, and type a name for the account. Do it in one
sitting — the link token expires quickly.

---

## The manual way (fallback)

Use this if the wizard fails or you'd rather do each step yourself. The example
adds a Chase card — swap in your own bank name.

Run all commands from the project root with your venv:
`cd ~/dev/finance-tracker/finance-tracker`

---

## 1. Create a link token

```
.venv/bin/python scripts/generate_link_token.py
```

Copy the value it prints — it starts with `link-`.

## 2. Open Plaid Link and connect the bank

1. Open `index.html`, replace the `linkToken` value (line ~10) with the token from step 1, save.
2. Open `index.html` in your browser (double-click it).
3. Log into the new bank in the popup.
4. When you see **"Success!"**, copy the `public_token` from the alert.

## 3. Exchange it for an access token

```
.venv/bin/python scripts/exchange_token.py
```

Paste the `public_token` when prompted. Copy the `access_token` it prints — it
starts with `access-`.

## 4. Save the token in `.env`

Add one line. Give it a clear, unique name:

```
PLAID_TOKEN_CHASE=access-production-xxxxxxxx
```

Secrets live only in `.env` — never in `config.yaml`.

## 5. Register the account in `config.yaml`

Add an entry under `accounts:`. The `access_token_env` must **exactly match**
the name you used in `.env`:

```yaml
  - name: "Chase Freedom"
    access_token_env: PLAID_TOKEN_CHASE
    enabled: true
```

## 6. Test it

```
.venv/bin/python -m src.main --window today --no-notify
```

You should see a line like `[Chase Freedom] N transactions`. Done — the next
5 PM run and the dashboard will include it automatically.

---

## Checklist

- [ ] `link-` token generated
- [ ] pasted into `index.html`, connected the bank, copied the `public_token`
- [ ] `access-` token from `exchange_token.py`
- [ ] token saved in `.env` as `PLAID_TOKEN_<NAME>`
- [ ] account added to `config.yaml` with matching `access_token_env`
- [ ] test run shows the new account

## Turning an account on/off

Flip `enabled: true` / `false` in `config.yaml`. No code changes. Set
`settings.pull_all: true` to pull every account regardless of the toggles.

## Optional: multiple cards under one login

If one bank login exposes several cards and you want them as separate rows,
add an `account_ids` filter to each entry:

```yaml
  - name: "Chase Sapphire"
    access_token_env: PLAID_TOKEN_CHASE
    account_ids: ["<account_id>"]
    enabled: true
```

Ask me to enhance `scripts/check_accounts.py` if you need to list the
`account_id` values for a login — the current version reads the legacy
`PLAID_ACCESS_TOKEN` only.

## Common gotchas

- **Nothing pulled?** The `access_token_env` name in `config.yaml` must match
  the variable name in `.env` character-for-character.
- **Link token error?** It's short-lived — regenerate (step 1) and redo it in
  one go.
- **Wrong environment?** The token's environment (production/sandbox) must
  match `PLAID_HOST` in `.env`.
