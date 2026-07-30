#!/usr/bin/env python3
"""Entrypoint the OpenClaw finance_spend tool shells out to.

Contract:
  args : --category <enum> --window <enum>
  out  : a single JSON object on stdout, e.g.
         {"summary": "...", "total": 123.45, "count": 7,
          "category": "dining", "window": "last_7_days"}

The model never runs this — index.js does, with enum-validated args. All the
finance logic lives on the Python side, so answers are deterministic and
testable. This reuses the existing src/ pipeline (config -> dates -> fetch ->
filter) and adds category filtering on top.
"""

import argparse
import json
import sys
from pathlib import Path

# Make the repo root importable (openclaw/bin/ -> repo root is two levels up).
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CATEGORIES = [
    "all", "dining", "groceries", "travel", "transport", "shopping",
    "entertainment", "bills_utilities", "medical", "personal_care",
]
WINDOWS = ["today", "last_7_days", "mtd", "last_30_days"]

WINDOW_LABEL = {
    "today": "today",
    "last_7_days": "the last 7 days",
    "mtd": "this month so far",
    "last_30_days": "the last 30 days",
}

# Map our friendly enums onto Plaid's personal_finance_category.
# Most map to a `primary` code. dining/groceries share FOOD_AND_DRINK at the
# primary level, so they are split on the `detailed` code.
_GROCERIES_DETAILED = "FOOD_AND_DRINK_GROCERIES"
CATEGORY_MATCH = {
    "dining":          {"primary": {"FOOD_AND_DRINK"}, "exclude_detailed": {_GROCERIES_DETAILED}},
    "groceries":       {"detailed": {_GROCERIES_DETAILED}},
    "travel":          {"primary": {"TRAVEL"}},
    "transport":       {"primary": {"TRANSPORTATION"}},
    "shopping":        {"primary": {"GENERAL_MERCHANDISE"}},
    "entertainment":   {"primary": {"ENTERTAINMENT"}},
    "bills_utilities": {"primary": {"RENT_AND_UTILITIES"}},
    "medical":         {"primary": {"MEDICAL"}},
    "personal_care":   {"primary": {"PERSONAL_CARE"}},
}


def _pfc_codes(row):
    """Return (primary, detailed) uppercase codes for a transaction row.

    Handles Plaid's personal_finance_category dict, with a fallback to the
    legacy `category` list. Missing -> ("", "").
    """
    pfc = row.get("personal_finance_category")
    if isinstance(pfc, dict):
        primary = str(pfc.get("primary") or "").upper()
        detailed = str(pfc.get("detailed") or "").upper()
        if primary:
            return primary, detailed
    legacy = row.get("category")
    if isinstance(legacy, (list, tuple)) and legacy:
        return str(legacy[0]).upper().replace(" ", "_"), ""
    return "", ""


def matches_category(row, category):
    """True if a transaction row belongs to the requested friendly category."""
    if category == "all":
        return True
    rule = CATEGORY_MATCH.get(category)
    if not rule:
        return False
    primary, detailed = _pfc_codes(row)
    if "detailed" in rule:
        if detailed not in rule["detailed"]:
            return False
    if "primary" in rule:
        if primary not in rule["primary"]:
            return False
    if detailed in rule.get("exclude_detailed", set()):
        return False
    return True


def filter_by_category(df, category):
    """Filter a cleaned expense DataFrame to one friendly category."""
    if category == "all" or df.empty:
        return df
    mask = df.apply(lambda r: matches_category(r, category), axis=1)
    return df[mask].reset_index(drop=True)


def _format_summary(df, category, window):
    label = WINDOW_LABEL[window]
    scope = "across all categories" if category == "all" else f"on {category}"
    if df.empty:
        return f"No spending found {scope} in {label}.", 0.0, 0

    total = float(df["amount"].sum())
    count = int(len(df))
    lines = [f"You spent ${total:,.2f} {scope} in {label} ({count} transactions)."]

    # A few biggest line items for context.
    top = df.sort_values("amount", ascending=False).head(3)
    if len(top):
        lines.append("Top:")
        for _, r in top.iterrows():
            name = str(r.get("merchant") or r.get("name") or "Unknown")[:24]
            lines.append(f"  • {name}: ${float(r.get('amount', 0)):,.2f}")
    return "\n".join(lines), total, count


def run_query(category: str, window: str) -> dict:
    """Run the real pipeline for one category + window and summarize."""
    from src.config_loader import load_config
    from src.dates import resolve_window
    from src.fetcher import fetch_all_transactions
    from src.processor import filter_expenses

    config = load_config()
    start, end = resolve_window(config["fetch"], window=window)
    transactions = fetch_all_transactions(
        mode="range", start=start, end=end, config=config
    )
    keywords = config.get("transfer_filters", {}).get("keywords", [])
    clean_df = filter_expenses(transactions, transfer_keywords=keywords)
    scoped_df = filter_by_category(clean_df, category)

    summary, total, count = _format_summary(scoped_df, category, window)
    return {
        "summary": summary,
        "total": round(total, 2),
        "count": count,
        "category": category,
        "window": window,
        "range": {"start": str(start), "end": str(end)},
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--category", default="all", choices=CATEGORIES)
    p.add_argument("--window", default="last_7_days", choices=WINDOWS)
    args = p.parse_args()

    try:
        print(json.dumps(run_query(args.category, args.window)))
        return 0
    except Exception as e:  # keep errors machine-readable for the JS shim
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
