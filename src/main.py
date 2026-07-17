"""Entry point for the spend tracker.

Examples:
  python -m src.main                          # config default: range, last_7_days
  python -m src.main --window mtd             # month-to-date report
  python -m src.main --start 2026-06-01 --end 2026-06-30
  python -m src.main --sync                   # incremental "new charges" mode
  python -m src.main --pull-all --no-notify   # every account, print only
"""
import argparse

from src.config_loader import load_config
from src.dates import resolve_window
from src.fetcher import fetch_all_transactions
from src.processor import filter_expenses
from src.summarizer import generate_summary
from src.notifier import send_ntfy_alert


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Personal spend tracker")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--sync", action="store_true", help="Incremental cursor mode")
    mode.add_argument("--range", dest="range_mode", action="store_true",
                      help="Date-range mode (default)")
    p.add_argument("--window", help="today|last_2_days|last_7_days|mtd|last_30_days|custom")
    p.add_argument("--start", help="Start date YYYY-MM-DD (range mode)")
    p.add_argument("--end", help="End date YYYY-MM-DD (defaults to today)")
    p.add_argument("--pull-all", action="store_true",
                   help="Pull every account, ignoring 'enabled' toggles")
    p.add_argument("--no-notify", action="store_true",
                   help="Print the report but do not send an ntfy alert")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    try:
        config = load_config()
    except RuntimeError as e:
        print(f"❌ Configuration error: {e}")
        return

    if args.pull_all:
        config["settings"]["pull_all"] = True

    mode = config["fetch"].get("mode", "range")
    if args.sync:
        mode = "sync"
    elif args.range_mode:
        mode = "range"

    print("🚀 Starting spend tracker...")

    start = end = None
    if mode == "range":
        try:
            start, end = resolve_window(
                config["fetch"], start=args.start, end=args.end, window=args.window
            )
        except ValueError as e:
            print(f"❌ Date error: {e}")
            return
        print(f"Mode: range | Window: {start} → {end} (inclusive)")
    else:
        print("Mode: sync (incremental)")

    transactions = fetch_all_transactions(mode=mode, start=start, end=end, config=config)
    print(f"Fetched {len(transactions)} raw transactions.")

    keywords = config.get("transfer_filters", {}).get("keywords", [])
    clean_df = filter_expenses(transactions, transfer_keywords=keywords)

    report = generate_summary(clean_df)
    print("\n" + report + "\n")

    if clean_df.empty:
        print("No relevant expenses to report.")
        return
    if args.no_notify:
        print("(--no-notify set: skipping ntfy alert)")
        return

    send_ntfy_alert(report, title="Finance Report")
    print("✅ Report sent.")


if __name__ == "__main__":
    main()
