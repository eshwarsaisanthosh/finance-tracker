"""Utility: list the accounts (and their IDs) under each configured login.

Queries every distinct access token in config.yaml, so you can find the
account_id values needed to filter a login to specific cards (e.g. keep the
credit card, drop the checking account). Shows type/subtype to tell them apart.
"""
import _bootstrap  # noqa: F401

from plaid.model.accounts_get_request import AccountsGetRequest

from src.config_loader import load_config
from src.plaid_client import get_plaid_client


def main():
    config = load_config()
    client = get_plaid_client(config)

    seen = set()
    for acct in config["accounts"]:
        env = acct["access_token_env"]
        if env in seen:
            continue
        seen.add(env)

        if not acct["access_token"]:
            print(f"\n=== {env} ===\n  (token not set in .env — skipping)")
            continue

        print(f"\n=== {acct['name']}  [{env}] ===")
        try:
            resp = client.accounts_get(
                AccountsGetRequest(access_token=acct["access_token"])
            )
        except Exception as e:
            print(f"  error: {e}")
            continue

        for a in resp["accounts"]:
            official = getattr(a, "official_name", None) or ""
            print(
                f"  {a.name}  {('('+official+')') if official else ''}\n"
                f"     type={a.type}/{a.subtype}  mask={a.mask}\n"
                f"     account_id={a.account_id}"
            )


if __name__ == "__main__":
    main()
