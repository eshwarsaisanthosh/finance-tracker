"""Generate a self-contained spend dashboard (dashboard.html).

Reads transactions (live from Plaid over the last N days, or from a CSV via
--from-csv) and writes one standalone HTML file with a normalized model
embedded. All analytics (KPIs, budgets, monthly stacked, subscriptions,
category drift, cashflow, insights, the interactive table) are computed in
the page from that model, so the account checkboxes re-filter everything and
/api/refresh only needs to return fresh data.

Usage:
  python -m scripts.generate_dashboard                 # live, last ~110 days
  python scripts/generate_dashboard.py --from-csv data/transactions.csv
  python scripts/generate_dashboard.py --from-csv f.csv --today 2026-07-16
"""
import argparse
import csv
import datetime

import _bootstrap  # noqa: F401
from _bootstrap import PROJECT_ROOT

import pandas as pd

from src.enrich import categorize, clean_merchant
from src.processor import filter_expenses
from src.template_dashboard import render_html

WINDOW_DAYS = 90

# Categories that are money movement, not spending — excluded from the dashboard.
NONSPEND_CATEGORIES = {
    "Transfer in", "Transfer out", "Loan payments", "Credit card payment",
    "Payment", "Transfer",
}


def _keywords():
    try:
        from src.config_loader import load_config
        return load_config().get("transfer_filters", {}).get("keywords", [])
    except Exception:
        return ["PAYMENT TO", "TRANSFER", "CREDIT CARD BILL", "AUTOPAY"]


def _budgets():
    try:
        from src.config_loader import load_budgets
        return load_budgets()
    except Exception:
        return {}


def _default_account():
    """Account name to assume when a CSV has no Account column.

    Falls back to the first enabled account in config.yaml (so budgets match),
    else 'Unknown'.
    """
    try:
        from src.config_loader import load_config
        cfg = load_config()
        for a in cfg.get("accounts", []):
            if a.get("enabled"):
                return a["name"]
    except Exception:
        pass
    return "Unknown"


def compute_model(rows, today=None, keywords=None):
    """Build the dashboard model: metadata + budgets + a normalized txn list.

    Every panel in the page is derived client-side from `transactions`, so
    this stays small and the UI stays consistent under account filtering.
    """
    today = today or datetime.date.today()
    keywords = _keywords() if keywords is None else keywords

    base = {
        "generatedAt": datetime.datetime.now().isoformat(timespec="minutes"),
        "today": {"y": today.year, "m": today.month, "d": today.day},
        "windowDays": WINDOW_DAYS,
        "minDate": None,
        "maxDate": None,
        "accounts": [],
        "budgets": _budgets(),
        "transactions": [],
    }

    df = filter_expenses(rows, transfer_keywords=keywords)
    if df.empty or "date" not in df.columns:
        return base

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return base
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df = df[df["amount"] > 0]
    if df.empty:
        return base

    txns = []
    for _, r in df.sort_values("date", ascending=False).iterrows():
        cat = str(r.get("category") or "Services")
        if cat in NONSPEND_CATEGORIES:
            continue  # transfers / card payments aren't spending
        dt = r["date"]
        acct = str(r.get("account") or "Unknown")
        txns.append({
            "raw": dt.strftime("%Y-%m-%d"),
            "d": dt.strftime("%b %d"),
            "m": str(r.get("merchant") or r.get("name") or "Unknown"),
            "cat": cat,
            "a": acct,
            "g": str(r.get("group") or acct),
            "v": round(float(r.get("amount", 0)), 2),
        })

    base["transactions"] = txns
    base["accounts"] = sorted({t["a"] for t in txns})
    base["minDate"] = df["date"].min().strftime("%Y-%m-%d")
    base["maxDate"] = df["date"].max().strftime("%Y-%m-%d")
    return base


def load_from_csv(path):
    """Load rows from a CSV, enriching any columns the file doesn't carry.

    Handles both the rich 7-column export (Date,Name,Amount,Account,Category,
    Merchant,ID) and a bare 4-column file (Date,Name,Amount,ID): missing
    Category is inferred from the name, Merchant is cleaned from the name, and
    a missing Account defaults to the first enabled account in config.yaml.
    """
    default_acct = None
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = set(reader.fieldnames or [])
        has_account = "Account" in cols
        has_category = "Category" in cols
        has_merchant = "Merchant" in cols
        has_group = "Group" in cols
        if not has_account:
            default_acct = _default_account()
        for r in reader:
            name = (r.get("Name") or "").strip()
            acct = (r.get("Account") if has_account else default_acct) or "Unknown"
            rows.append({
                "date": r.get("Date"),
                "name": name,
                "amount": float(r.get("Amount") or 0),
                "account": acct,
                "group": (r.get("Group") if has_group else acct) or acct,
                "category": (r.get("Category") if has_category else categorize(name)) or categorize(name),
                "merchant": (r.get("Merchant") if has_merchant else clean_merchant(name)) or clean_merchant(name),
                "id": r.get("ID", ""),
            })
    return rows


def load_live(days):
    from src.config_loader import load_config
    from src.enrich import normalize
    from src.fetcher import fetch_all_transactions
    config = load_config()
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    raw = fetch_all_transactions(mode="range", start=start, end=end, config=config)
    return normalize(raw)


def main(argv=None):
    p = argparse.ArgumentParser(description="Generate the spend dashboard HTML")
    p.add_argument("--from-csv", dest="csv", help="Build from a CSV")
    p.add_argument("--out", default=str(PROJECT_ROOT / "dashboard.html"))
    p.add_argument("--today", help="Override 'today' (YYYY-MM-DD), for testing")
    p.add_argument("--days", type=int, default=WINDOW_DAYS + 20,
                   help="Days of history to pull (live mode)")
    p.add_argument("--no-open", action="store_true",
                   help="Don't open the dashboard in a browser afterwards "
                        "(used by the headless daily job)")
    args = p.parse_args(argv)

    today = datetime.date.fromisoformat(args.today) if args.today else None
    rows = load_from_csv(args.csv) if args.csv else load_live(args.days)

    model = compute_model(rows, today=today)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render_html(model))
    print(f"Dashboard written to {args.out}  "
          f"({len(model['transactions'])} transactions, "
          f"{len(model['accounts'])} account(s): {', '.join(model['accounts']) or '—'})")

    if not args.no_open:
        import os
        import webbrowser
        url = "file://" + os.path.abspath(args.out)
        try:
            webbrowser.open_new_tab(url)
            print(f"Opening {url}")
        except Exception as e:
            print(f"(Could not auto-open a browser: {e})")


if __name__ == "__main__":
    main()
