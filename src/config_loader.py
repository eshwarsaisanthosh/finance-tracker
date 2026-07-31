"""Central configuration loader.

Merges secrets from .env with declarative settings from config/config.yaml.

Multi-account model: each account entry names an env var (access_token_env)
that holds its Plaid access token. Tokens are secrets and never live in yaml.
A single legacy PLAID_ACCESS_TOKEN is still honoured if no accounts are defined.
"""
import os
import shutil
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
CONFIG_EXAMPLE = PROJECT_ROOT / "config" / "config.example.yaml"
BUDGETS_PATH = PROJECT_ROOT / "config" / "budgets.yaml"
BUDGETS_EXAMPLE = PROJECT_ROOT / "config" / "budgets.example.yaml"

load_dotenv(PROJECT_ROOT / ".env")


def _seed_from_example(real, example):
    """On first run, create a personal config from its committed template.

    The personal files (config.yaml, budgets.yaml) are gitignored, so a fresh
    clone won't have them — copy the example so the app works out of the box
    without ever overwriting an existing local file.
    """
    if not real.exists() and example.exists():
        shutil.copy(example, real)
        print(f"Created config/{real.name} from config/{example.name} — "
              f"edit it with your own accounts.")


def _load_yaml():
    _seed_from_example(CONFIG_PATH, CONFIG_EXAMPLE)
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f) or {}


def load_budgets():
    """Return per-card per-category monthly budgets.

    Shape: {account_name: {category: monthly_target}}. Empty dict if the file
    is missing, so the dashboard degrades gracefully (no budget panels).
    """
    _seed_from_example(BUDGETS_PATH, BUDGETS_EXAMPLE)
    if not BUDGETS_PATH.exists():
        return {}
    with open(BUDGETS_PATH, "r") as f:
        data = yaml.safe_load(f) or {}
    budgets = data.get("budgets", {}) or {}
    # Coerce values to numbers; drop anything unparseable.
    clean = {}
    for card, cats in budgets.items():
        if not isinstance(cats, dict):
            continue
        clean[card] = {}
        for cat, amt in cats.items():
            try:
                clean[card][cat] = float(amt)
            except (TypeError, ValueError):
                continue
    return clean


def save_budgets(budgets):
    """Persist per-card per-category budgets back to config/budgets.yaml.

    `budgets` is {account_name: {category: monthly_target}}. Values are
    written as ints where whole, else floats. Overwrites the file's budgets:
    block while preserving the leading comment header if present.
    """
    payload = {"budgets": {
        card: {cat: (int(v) if float(v).is_integer() else float(v))
               for cat, v in cats.items()}
        for card, cats in budgets.items()
    }}
    header = ""
    if BUDGETS_PATH.exists():
        existing = BUDGETS_PATH.read_text()
        # keep the comment header (lines before the first non-comment/non-blank)
        lines = []
        for ln in existing.splitlines():
            if ln.strip() and not ln.lstrip().startswith("#"):
                break
            lines.append(ln)
        header = "\n".join(lines).rstrip() + "\n\n" if lines else ""
    BUDGETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BUDGETS_PATH, "w") as f:
        if header:
            f.write(header)
        yaml.safe_dump(payload, f, default_flow_style=False, sort_keys=False,
                       allow_unicode=True)


def _resolve_host(yaml_cfg):
    """Prefer an explicit PLAID_HOST; otherwise derive it from plaid_env."""
    host = os.getenv("PLAID_HOST")
    if host:
        return host.rstrip("/")
    env = yaml_cfg.get("app_settings", {}).get("plaid_env", "sandbox")
    return f"https://{env}.plaid.com"


def _resolve_accounts(yaml_cfg):
    """Turn yaml account entries into records with the token resolved from env."""
    accounts = []
    for entry in yaml_cfg.get("accounts", []) or []:
        token_env = entry.get("access_token_env")
        token = os.getenv(token_env) if token_env else None
        accounts.append(
            {
                "name": entry.get("name") or token_env or "Unnamed",
                "access_token_env": token_env,
                "access_token": token,
                "account_ids": entry.get("account_ids") or [],
                "enabled": bool(entry.get("enabled", True)),
            }
        )
    return accounts


def load_config():
    """Return a single structured config dict.

    Keys: plaid, accounts, settings, fetch, app_settings, transfer_filters.
    """
    yaml_cfg = _load_yaml()

    plaid_cfg = {
        "client_id": os.getenv("PLAID_CLIENT_ID"),
        "secret": os.getenv("PLAID_SECRET"),
        "host": _resolve_host(yaml_cfg),
        "access_token": os.getenv("PLAID_ACCESS_TOKEN"),  # legacy / optional
        "item_id": os.getenv("PLAID_ITEM_ID"),
    }
    if not plaid_cfg["client_id"] or not plaid_cfg["secret"]:
        raise RuntimeError(
            "Missing PLAID_CLIENT_ID / PLAID_SECRET. Add them to your .env file."
        )

    accounts = _resolve_accounts(yaml_cfg)
    # Legacy fallback: no accounts defined, but a single token exists.
    if not accounts and plaid_cfg["access_token"]:
        accounts = [
            {
                "name": "Default",
                "access_token_env": "PLAID_ACCESS_TOKEN",
                "access_token": plaid_cfg["access_token"],
                "account_ids": [],
                "enabled": True,
            }
        ]

    settings = yaml_cfg.get("settings", {}) or {}
    pull_all = bool(settings.get("pull_all", False))

    fetch = dict(yaml_cfg.get("fetch", {}) or {})
    fetch.setdefault("mode", "range")
    fetch.setdefault("window", "last_7_days")
    fetch.setdefault("custom", {})

    # Validate that selected accounts actually have a resolvable token.
    selected = [a for a in accounts if pull_all or a["enabled"]]
    if selected and not any(a["access_token"] for a in selected):
        missing = ", ".join(a["access_token_env"] or a["name"] for a in selected)
        raise RuntimeError(
            "No access token resolved for the selected account(s). "
            f"Set these in your .env: {missing}"
        )

    return {
        "plaid": plaid_cfg,
        "accounts": accounts,
        "settings": {"pull_all": pull_all},
        "fetch": fetch,
        "app_settings": yaml_cfg.get("app_settings", {}),
        "transfer_filters": yaml_cfg.get("transfer_filters", {}),
    }
