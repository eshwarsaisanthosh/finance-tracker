"""Generate a self-contained spend dashboard (dashboard.html).

Reads transactions (live from Plaid over the last N days, or from an enriched
CSV via --from-csv), computes the model, and writes one standalone HTML file
with the data embedded. No server, no external assets.

Usage:
  python -m scripts.generate_dashboard                 # live, last ~100 days
  python scripts/generate_dashboard.py --from-csv data/transactions.csv
  python scripts/generate_dashboard.py --from-csv f.csv --today 2026-07-16
"""
import argparse
import csv
import datetime

import _bootstrap  # noqa: F401
from _bootstrap import PROJECT_ROOT

import pandas as pd

from src.enrich import initials
from src.processor import filter_expenses
from src.template_dashboard import render_html

WINDOW_DAYS = 90


def _keywords():
    try:
        from src.config_loader import load_config
        return load_config().get("transfer_filters", {}).get("keywords", [])
    except Exception:
        return ["PAYMENT TO", "TRANSFER", "CREDIT CARD BILL"]


def _round(x):
    return int(round(float(x)))


def compute_model(rows, today=None, keywords=None):
    """Build the dashboard model.

    Month-scoped data (calendar, hero, per-month stats) comes from
    `dailyByDate` / `detailByDate`. The `by account` and `top categories`
    panels are a fixed rolling-90-day view (`rolling90`).
    """
    today = today or datetime.date.today()
    keywords = _keywords() if keywords is None else keywords

    base = {
        "generatedAt": datetime.datetime.now().isoformat(timespec="minutes"),
        "today": {"y": today.year, "m": today.month, "d": today.day},
        "windowDays": WINDOW_DAYS,
        "minDate": None, "maxDate": None,
        "dailyByDate": {}, "detailByDate": {},
        "rolling90": {"total": 0, "dailyAvg": 0, "categories": [], "accounts": []},
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
    df["ymd"] = df["date"].dt.strftime("%Y-%m-%d")

    # Month-scoped: spend + transactions keyed by full date.
    daily = df.groupby("ymd")["amount"].sum()
    base["dailyByDate"] = {k: _round(v) for k, v in daily.items()}

    detail = {}
    for ymd, g in df.groupby("ymd"):
        items = []
        for _, r in g.sort_values("amount", ascending=False).iterrows():
            acct = str(r.get("account", "Unknown"))
            items.append({
                "code": initials(acct),
                "acct": acct,
                "merchant": str(r.get("merchant") or r.get("name") or "Unknown"),
                "cat": str(r.get("category") or "Uncategorized"),
                "amt": _round(r.get("amount", 0)),
            })
        detail[ymd] = items
    base["detailByDate"] = detail

    base["minDate"] = df["date"].min().strftime("%Y-%m-%d")
    base["maxDate"] = df["date"].max().strftime("%Y-%m-%d")

    # Rolling 90-day: account + category breakdowns.
    today_ts = pd.Timestamp(today)
    win = df[df["date"] >= (today_ts - pd.Timedelta(days=WINDOW_DAYS - 1))]
    total90 = float(win["amount"].sum())
    cats = win.groupby("category")["amount"].sum().sort_values(ascending=False).head(5)
    accs = win.groupby("account")["amount"].sum().sort_values(ascending=False)
    base["rolling90"] = {
        "total": _round(total90),
        "dailyAvg": _round(total90 / WINDOW_DAYS),
        "categories": [[str(k), _round(v)] for k, v in cats.items()],
        "accounts": [[str(k), _round(v), initials(str(k))] for k, v in accs.items()],
    }
    return base


def load_from_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "date": r.get("Date"),
                "name": r.get("Name", ""),
                "amount": float(r.get("Amount") or 0),
                "account": r.get("Account", "Unknown"),
                "category": r.get("Category", "Uncategorized"),
                "merchant": r.get("Merchant", ""),
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
    p.add_argument("--from-csv", dest="csv", help="Build from an enriched CSV")
    p.add_argument("--out", default=str(PROJECT_ROOT / "dashboard.html"))
    p.add_argument("--today", help="Override 'today' (YYYY-MM-DD), for testing")
    p.add_argument("--days", type=int, default=WINDOW_DAYS + 20,
                   help="Days of history to pull (live mode)")
    args = p.parse_args(argv)

    today = datetime.date.fromisoformat(args.today) if args.today else None
    rows = load_from_csv(args.csv) if args.csv else load_live(args.days)

    model = compute_model(rows, today=today)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render_html(model))
    print(f"Dashboard written to {args.out}  (90d ${model['rolling90']['total']:,}, "
          f"{len(model['detailByDate'])} active days)")


if __name__ == "__main__":
    main()
