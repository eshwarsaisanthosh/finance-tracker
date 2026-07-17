"""Utility: pull up to 2 years of history via the transactions/get endpoint.

Useful for a one-time backfill. For incremental daily runs, prefer the sync
flow in src/fetcher.py (cursor based).
"""
import datetime

import _bootstrap  # noqa: F401

from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import (
    TransactionsGetRequestOptions,
)

from src.config_loader import load_config
from src.plaid_client import get_plaid_client


def fetch_historical_transactions():
    config = load_config()
    client = get_plaid_client(config)
    access_token = config["plaid"]["access_token"]

    start_date = (datetime.datetime.now() - datetime.timedelta(days=2 * 365)).date()
    end_date = datetime.datetime.now().date()

    all_transactions = []
    batch_size = 500  # Plaid's maximum per page
    offset = 0

    print(f"Fetching transactions from {start_date} to {end_date}...")

    while True:
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(count=batch_size, offset=offset),
        )
        response = client.transactions_get(request)
        transactions = response["transactions"]
        total_available = response["total_transactions"]

        all_transactions.extend(transactions)
        print(
            f"Progress: {len(all_transactions)} of {total_available} "
            "total available transactions."
        )

        offset += batch_size
        if len(all_transactions) >= total_available:
            break

    return all_transactions


def main():
    try:
        transactions = fetch_historical_transactions()
    except Exception as e:
        print(f"An error occurred: {e}")
        return

    print(f"\nSUCCESS: Retrieved a total of {len(transactions)} transactions.")
    if transactions:
        first = transactions[0]
        print(f"Example transaction: {first.name} - {first.amount}")


if __name__ == "__main__":
    main()
