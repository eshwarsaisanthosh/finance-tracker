"""Fetch transactions from Plaid across one or more card logins.

Two modes:
  - range: transactions_get over a date window (the spend-tracker default).
  - sync:  transactions_sync incremental, with a per-account cursor stored in
           config/cursors.json (used for "notify me of new charges").

Each returned transaction is a plain dict tagged with its account name so the
report can break spend down per card.
"""
import datetime
import json

from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import (
    TransactionsGetRequestOptions,
)

from src.config_loader import load_config, PROJECT_ROOT
from src.plaid_client import get_plaid_client

CURSORS_FILE = PROJECT_ROOT / "config" / "cursors.json"
ACCOUNT_MAP_FILE = PROJECT_ROOT / "config" / "account_map.json"


def _load_account_map():
    """account_id -> friendly sub-account name (e.g. 'WF Checking'). Optional."""
    try:
        return json.loads(ACCOUNT_MAP_FILE.read_text())
    except Exception:
        return {}


_ACCOUNT_MAP = _load_account_map()


def get_active_accounts(config, warn=True):
    """Accounts to pull: all if settings.pull_all, else those enabled.

    Only accounts with a resolved token are returned. Enabled accounts whose
    token is missing from .env are warned about (a common config mistake)
    rather than silently skipped.
    """
    pull_all = config["settings"]["pull_all"]
    selected = [a for a in config["accounts"] if pull_all or a["enabled"]]
    active = []
    for a in selected:
        if a["access_token"]:
            active.append(a)
        elif warn:
            print(f"⚠️  {a['name']}: token '{a['access_token_env']}' "
                  "is not set in .env — skipping this account.")
    return active


def _to_dict(txn, account_name):
    d = txn.to_dict() if hasattr(txn, "to_dict") else dict(txn)
    # `group` = the login/institution (config name); `account` = the specific
    # sub-account (checking / savings / a card), resolved from account_map.json
    # by account_id. Falls back to the login name when the id isn't mapped, so
    # a single-account login stays a flat, ungrouped chip.
    d["group"] = account_name
    sub = _ACCOUNT_MAP.get(d.get("account_id"))
    d["account"] = sub or account_name
    if isinstance(d.get("date"), (datetime.date, datetime.datetime)):
        d["date"] = d["date"].isoformat()
    return d


def _filter_account_ids(records, account_ids):
    if not account_ids:
        return records
    wanted = set(account_ids)
    return [r for r in records if r.get("account_id") in wanted]


def _load_cursors():
    if CURSORS_FILE.exists():
        try:
            return json.loads(CURSORS_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_cursors(cursors):
    CURSORS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CURSORS_FILE.write_text(json.dumps(cursors, indent=2))


def fetch_range(client, account, start, end):
    """Pull all transactions for one account between start and end (inclusive)."""
    out = []
    offset = 0
    batch = 500  # Plaid max per page
    while True:
        request = TransactionsGetRequest(
            access_token=account["access_token"],
            start_date=start,
            end_date=end,
            options=TransactionsGetRequestOptions(count=batch, offset=offset),
        )
        response = client.transactions_get(request)
        txns = response["transactions"]
        total = response["total_transactions"]
        out.extend(_to_dict(t, account["name"]) for t in txns)
        offset += batch
        if len(out) >= total or not txns:
            break
    return _filter_account_ids(out, account["account_ids"])


def fetch_sync(client, account, cursors):
    """Incrementally pull new transactions for one account, advancing its cursor."""
    key = account["access_token_env"] or account["name"]
    cursor = cursors.get(key)
    added = []
    has_more = True
    while has_more:
        args = {"access_token": account["access_token"]}
        if cursor:
            args["cursor"] = cursor
        response = client.transactions_sync(TransactionsSyncRequest(**args))
        added.extend(_to_dict(t, account["name"]) for t in response.added)
        cursor = response.next_cursor
        has_more = response.has_more
    cursors[key] = cursor
    return _filter_account_ids(added, account["account_ids"])


def fetch_all_transactions(mode="range", start=None, end=None, config=None):
    """Fetch across all active accounts. Returns a flat list of tagged dicts."""
    config = config or load_config()
    client = get_plaid_client(config)
    accounts = get_active_accounts(config)

    if not accounts:
        print("⚠️  No active accounts with a resolvable token.")
        return []

    all_txns = []

    if mode == "sync":
        cursors = _load_cursors()
        for acct in accounts:
            try:
                txns = fetch_sync(client, acct, cursors)
                all_txns.extend(txns)
                print(f"  [{acct['name']}] {len(txns)} new")
            except Exception as e:
                print(f"  ⚠️  {acct['name']}: {e}")
        _save_cursors(cursors)
    else:  # range
        for acct in accounts:
            try:
                txns = fetch_range(client, acct, start, end)
                all_txns.extend(txns)
                print(f"  [{acct['name']}] {len(txns)} transactions")
            except Exception as e:
                print(f"  ⚠️  {acct['name']}: {e}")

    return all_txns
