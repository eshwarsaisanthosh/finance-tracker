"""One-time setup: exchange a public_token (from Plaid Link) for an access_token.

Paste the resulting access_token into your .env as PLAID_ACCESS_TOKEN.
"""
import _bootstrap  # noqa: F401

from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)

from src.plaid_client import get_plaid_client


def main():
    client = get_plaid_client()
    public_token = input("Paste your public_token from the browser here: ").strip()

    try:
        request = ItemPublicTokenExchangeRequest(public_token=public_token)
        response = client.item_public_token_exchange(request)
    except Exception as e:
        print(f"An error occurred: {e}")
        return

    print("----------------------------------------")
    print(f"SUCCESS! Your access_token is: {response['access_token']}")
    print(f"Your item_id is: {response['item_id']}")
    print("Add these to your .env as PLAID_ACCESS_TOKEN and PLAID_ITEM_ID.")
    print("----------------------------------------")


if __name__ == "__main__":
    main()
