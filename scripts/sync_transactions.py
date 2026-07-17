"""Utility: run the incremental cursor-based sync across active accounts.

Thin wrapper around src.fetcher so there is only one sync implementation.
"""
import _bootstrap  # noqa: F401

from src.fetcher import fetch_all_transactions


def main():
    transactions = fetch_all_transactions(mode="sync")
    print(f"Sync complete. Total new/updated transactions: {len(transactions)}")


if __name__ == "__main__":
    main()
