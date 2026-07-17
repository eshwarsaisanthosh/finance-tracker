"""Resolve a fetch window into a concrete (start_date, end_date) pair.

All presets end *today* (local date) and are INCLUSIVE of today, e.g.
last_7_days = [today - 6, today] which is 7 calendar days counting today.
"""
import datetime

PRESETS = ("today", "last_2_days", "last_7_days", "mtd", "last_30_days", "custom")


def _today():
    return datetime.date.today()


def _parse(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value))


def _guard(start, end, today):
    if end > today:
        end = today
    if start > today:
        raise ValueError(f"start_date {start} is in the future")
    if end < start:
        raise ValueError(f"end_date {end} is before start_date {start}")
    return start, end


def _resolve_preset(window, today):
    if window == "today":
        start = today
    elif window == "last_2_days":
        start = today - datetime.timedelta(days=1)
    elif window == "last_7_days":
        start = today - datetime.timedelta(days=6)
    elif window == "last_30_days":
        start = today - datetime.timedelta(days=29)
    elif window == "mtd":
        start = today.replace(day=1)
    else:
        raise ValueError(
            f"Unknown window '{window}'. Valid: {', '.join(PRESETS)}"
        )
    return _guard(start, today, today)


def _resolve_custom(custom, today):
    end = _parse(custom.get("end_date")) or today
    start = _parse(custom.get("start_date"))
    if start is None:
        lookback = custom.get("lookback_days")
        if lookback:
            start = end - datetime.timedelta(days=int(lookback) - 1)  # inclusive
        else:
            start = end - datetime.timedelta(days=6)  # sensible fallback: last 7d
    return _guard(start, end, today)


def resolve_window(fetch_cfg, start=None, end=None, window=None):
    """Return (start_date, end_date) as datetime.date objects.

    Priority: explicit CLI start/end > CLI window > config window/custom.
    """
    today = _today()

    # 1. Explicit CLI dates win outright.
    if start or end:
        s = _parse(start)
        e = _parse(end) or today
        if s is None:
            s = e - datetime.timedelta(days=6)  # end-only -> last 7 days
        return _guard(s, e, today)

    # 2. Chosen window (CLI overrides config).
    chosen = window or fetch_cfg.get("window", "last_7_days")
    if chosen == "custom":
        return _resolve_custom(fetch_cfg.get("custom", {}) or {}, today)
    return _resolve_preset(chosen, today)
