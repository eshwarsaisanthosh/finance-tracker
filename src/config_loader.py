"""Central configuration loader.

Merges secrets from .env with declarative settings from config/config.yaml.

Multi-account model: each account entry names an env var (access_token_env)
that holds its Plaid access token. Tokens are secrets and never live in yaml.
A single legacy PLAID_ACCESS_TOKEN is still honoured if no accounts are defined.
"""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

load_dotenv(PROJECT_ROOT / ".env")


def _load_yaml():
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f) or {}


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
