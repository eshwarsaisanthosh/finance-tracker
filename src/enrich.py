"""Normalize raw Plaid transactions into clean rows for CSV / dashboard.

Pulls category and merchant out of Plaid's fields and adds a short account
code (initials) used to tag accounts compactly in the UI.
"""


def prettify_category(txn):
    """Turn Plaid's personal_finance_category into 'Food and drink' style text."""
    code = None
    pfc = txn.get("personal_finance_category")
    if isinstance(pfc, dict):
        code = pfc.get("primary")
    if not code:
        legacy = txn.get("category")
        if isinstance(legacy, (list, tuple)) and legacy:
            code = str(legacy[0])
    if not code:
        return "Uncategorized"
    words = [w for w in str(code).replace("-", "_").split("_") if w]
    s = " ".join(w.lower() for w in words)
    return (s[:1].upper() + s[1:]) if s else "Uncategorized"


def merchant_of(txn):
    return txn.get("merchant_name") or txn.get("name") or "Unknown"


def initials(name):
    parts = [p for p in str(name).split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return (str(name)[:2]).upper() if name else "?"


def normalize(txns):
    """Return clean row dicts: date, name, amount, account, category, merchant, id."""
    rows = []
    for t in txns:
        rows.append(
            {
                "date": t.get("date"),
                "name": t.get("name") or "",
                "amount": float(t.get("amount") or 0),
                "account": t.get("account") or "Unknown",
                "category": prettify_category(t),
                "merchant": merchant_of(t),
                "id": t.get("transaction_id") or "",
            }
        )
    return rows
