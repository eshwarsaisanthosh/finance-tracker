"""Utility: export recent transactions to data/transactions.csv, enriched with
category and merchant. Pulls across all active accounts (see config.yaml).
"""
import csv
import datetime

import _bootstrap  # noqa: F401
from _bootstrap import PROJECT_ROOT

from src.config_loader import load_config
from src.enrich import normalize
from src.fetcher import fetch_all_transactions


def main(days=730):
    config = load_config()
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    print(f"Fetching {start} .. {end} across active accounts...")

    raw = fetch_all_transactions(mode="range", start=start, end=end, config=config)
    rows = normalize(raw)

    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "transactions.csv"

    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Name", "Amount", "Account", "Category", "Merchant", "ID"])
        for r in rows:
            writer.writerow(
                [r["date"], r["name"], r["amount"], r["account"],
                 r["category"], r["merchant"], r["id"]]
            )

    print(f"Exported {len(rows)} transactions to {csv_path}")


if __name__ == "__main__":
    main()
