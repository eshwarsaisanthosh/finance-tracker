"""One-time setup (sandbox only): mint a test access_token without a real bank.

Uses Plaid's standard sandbox institution. Requires plaid_env to resolve to a
sandbox host, or run against the sandbox credentials directly.
"""
import _bootstrap  # noqa: F401

import plaid
from plaid.model.sandbox_public_token_create_request import (
    SandboxPublicTokenCreateRequest,
)
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.products import Products

from src.plaid_client import get_plaid_client


def main():
    print("Setting up Plaid client...")
    client = get_plaid_client()

    try:
        print("1. Creating a temporary public token...")
        # ins_109508 is Plaid's standard test bank (First Platypus Bank).
        pt_request = SandboxPublicTokenCreateRequest(
            institution_id="ins_109508",
            initial_products=[Products("transactions")],
        )
        pt_response = client.sandbox_public_token_create(pt_request)

        print("2. Exchanging it for an access token...")
        exchange_response = client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=pt_response["public_token"])
        )

        print("\n=== SUCCESS! ===")
        print(f"Your Sandbox Access Token:\n\n{exchange_response['access_token']}\n")
        print("Copy the token above into your .env as PLAID_ACCESS_TOKEN.")
    except plaid.ApiException as e:
        print(f"\nAPI Error: {e}")
        print("Check PLAID_CLIENT_ID / PLAID_SECRET and that you're on sandbox.")


if __name__ == "__main__":
    main()
