"""Generate a self-contained spend dashboard (dashboard.html).

Reads transactions (live from Plaid over the last N days, or from an enriched
CSV via --from-csv), computes the model, and writes one standalone HTML file
with the data embedded. No server, no external assets — drop it in a synced
folder and open on your phone.

Usage:
  python -m scripts.generate_dashboard                 # live, last 100 days
  python scripts/generate_dashboard.py --from-csv data/transactions.csv
  python scripts/generate_dashboard.py --from-csv f.csv --today 2026-07-16
"""
import argparse
import calendar as calmod
import csv
import datetime
import json

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
    """Build the dashboard model dict from normalized rows."""
    today = today or datetime.date.today()
    keywords = _keywords() if keywords is None else keywords

    y, m = today.year, today.month
    days_in_month = calmod.monthrange(y, m)[1]
    offset = (calmod.monthrange(y, m)[0] + 1) % 7  # Sunday-first column index

    base = {
        "generatedAt": datetime.datetime.now().isoformat(timespec="minutes"),
        "year": y, "month": m,
        "monthName": calmod.month_name[m],
        "daysInMonth": days_in_month,
        "offset": offset,
        "todayDay": today.day,
        "windowDays": WINDOW_DAYS,
        "mtd": 0, "pacePct": None, "dailyAvg90": 0, "projected": 0,
        "dailySpend": {}, "cumulative": [], "heat": [25, 60, 120],
        "categories": [], "detail": {},
    }

    df = filter_expenses(rows, transfer_keywords=keywords)
    if df.empty or "date" not in df.columns:
        return base

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    today_ts = pd.Timestamp(today)

    # --- current month ---
    month_df = df[(df["date"].dt.year == y) & (df["date"].dt.month == m)
                  & (df["date"] <= today_ts)]
    mtd = float(month_df["amount"].sum())

    daily = month_df.groupby(month_df["date"].dt.day)["amount"].sum()
    daily_spend = {int(d): _round(v) for d, v in daily.items()}

    cumulative, run = [], 0.0
    for d in range(1, today.day + 1):
        run += float(daily.get(d, 0.0))
        cumulative.append({"d": d, "v": _round(run)})

    # heat thresholds from the month's non-zero day totals
    vals = [v for v in daily.values if v > 0]
    if len(vals) >= 3:
        s = pd.Series(vals)
        heat = [_round(s.quantile(0.4)), _round(s.quantile(0.7)), _round(s.quantile(0.9))]
        heat = sorted(set(h for h in heat if h > 0)) or base["heat"]
        while len(heat) < 3:
            heat.append(heat[-1] + 1)
    else:
        heat = base["heat"]

    # --- pace vs last month, same point ---
    pm_y, pm_m = (y - 1, 12) if m == 1 else (y, m - 1)
    lm_df = df[(df["date"].dt.year == pm_y) & (df["date"].dt.month == pm_m)
               & (df["date"].dt.day <= today.day)]
    lm_total = float(lm_df["amount"].sum())
    pace = round((mtd - lm_total) / lm_total * 100) if lm_total > 0 else None

    # --- rolling 90-day figures ---
    win = df[df["date"] >= (today_ts - pd.Timedelta(days=WINDOW_DAYS - 1))]
    total90 = float(win["amount"].sum())
    daily_avg90 = _round(total90 / WINDOW_DAYS)
    projected = _round(mtd / today.day * days_in_month) if today.day else 0

    cats = (win.groupby("category")["amount"].sum()
            .sort_values(ascending=False).head(5))
    categories = [[str(k), _round(v)] for k, v in cats.items()]

    # --- per-day, per-account detail (current month) ---
    detail = {}
    for d, day_df in month_df.groupby(month_df["date"].dt.day):
        items = []
        for _, r in day_df.sort_values("amount", ascending=False).iterrows():
            acct = str(r.get("account", "Unknown"))
            items.append({
                "code": initials(acct),
                "acct": acct,
                "merchant": str(r.get("merchant") or r.get("name") or "Unknown"),
                "cat": str(r.get("category") or "Uncategorized"),
                "amt": _round(r.get("amount", 0)),
            })
        detail[str(int(d))] = items

    base.update({
        "mtd": _round(mtd), "pacePct": pace, "dailyAvg90": daily_avg90,
        "projected": projected, "dailySpend": daily_spend,
        "cumulative": cumulative, "heat": heat,
        "categories": categories, "detail": detail,
    })
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
    p.add_argument("--days", type=int, default=WINDOW_DAYS + 10,
                   help="How many days of history to pull (live mode)")
    args = p.parse_args(argv)

    today = datetime.date.fromisoformat(args.today) if args.today else None

    if args.csv:
        rows = load_from_csv(args.csv)
    else:
        rows = load_live(args.days)

    model = compute_model(rows, today=today)
    html = render_html(model)

    out = args.out
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard written to {out}  (MTD ${model['mtd']:,}, "
          f"{len(model['detail'])} active days)")


if __name__ == "__main__":
    main()
