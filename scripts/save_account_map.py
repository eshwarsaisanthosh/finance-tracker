"""One-time setup: fetch account names and save config/account_map.json.

Produces a { account_id: friendly_name } lookup used when exporting.
"""
import json

import _bootstrap  # noqa: F401
from _bootstrap import PROJECT_ROOT

from plaid.model.accounts_get_request import AccountsGetRequest

from src.config_loader import load_config
from src.plaid_client import get_plaid_client


def main():
    config = load_config()
    client = get_plaid_client(config)

    request = AccountsGetRequest(access_token=config["plaid"]["access_token"])
    response = client.accounts_get(request)

    account_map = {acc.account_id: acc.name for acc in response["accounts"]}

    out_path = PROJECT_ROOT / "config" / "account_map.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(account_map, f, indent=4)

    print(f"Mapping saved to {out_path}:")
    print(account_map)


if __name__ == "__main__":
    main()
