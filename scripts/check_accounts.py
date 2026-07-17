"""Utility: list the accounts available under the linked Plaid item."""
import _bootstrap  # noqa: F401

from plaid.model.accounts_get_request import AccountsGetRequest

from src.config_loader import load_config
from src.plaid_client import get_plaid_client


def main():
    config = load_config()
    client = get_plaid_client(config)

    request = AccountsGetRequest(access_token=config["plaid"]["access_token"])
    response = client.accounts_get(request)

    for account in response["accounts"]:
        print(
            f"Account Name: {account.name} | "
            f"Mask: {account.mask} | ID: {account.account_id}"
        )


if __name__ == "__main__":
    main()
