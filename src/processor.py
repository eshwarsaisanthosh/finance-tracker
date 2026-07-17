"""Clean raw Plaid transactions into a tidy DataFrame and drop transfers.

Transfers, credit-card payments and the like aren't real spending, so we
exclude them using the keyword list in config.yaml -> transfer_filters.
"""
import pandas as pd


def _to_records(transactions):
    """Coerce a mix of Plaid objects / dicts into plain dicts."""
    records = []
    for t in transactions:
        if hasattr(t, "to_dict"):
            records.append(t.to_dict())
        elif isinstance(t, dict):
            records.append(t)
        # Anything else (e.g. stray strings) is skipped.
    return records


def filter_expenses(transactions, transfer_keywords=None):
    """Return a cleaned DataFrame of real expenses.

    - Normalises dates.
    - Drops rows whose name matches a transfer keyword (case-insensitive).
    - Positive Plaid amounts are money out; negatives are inflows/refunds,
      which we exclude from an expense report.
    """
    records = _to_records(transactions)
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        # Keep outflows only (Plaid: positive = money leaving the account).
        df = df[df["amount"] > 0]

    # Filter out transfers / payments by name keyword.
    if transfer_keywords and "name" in df.columns:
        pattern = "|".join(pd.Series(transfer_keywords).str.strip())
        if pattern:
            mask = df["name"].fillna("").str.contains(pattern, case=False, regex=True)
            df = df[~mask]

    return df.reset_index(drop=True)
