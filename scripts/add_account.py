"""Interactive wizard: link a new bank account end-to-end in one command.

Replaces the six manual steps in docs/adding-an-account.md. It will:

  1. Generate a Plaid link token.
  2. Inject it into index.html and open the page in your browser.
  3. Take the public_token you copy from the browser and exchange it.
  4. Let you pick which card(s) under that login to track.
  5. Write the access token to .env (PLAID_TOKEN_<NAME>).
  6. Append the account entry to config/config.yaml.
  7. Optionally run a test fetch.

.env and config.yaml are backed up (timestamped .bak) before any edit.

Run from the project root:
    .venv/bin/python scripts/add_account.py
"""
import re
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

import _bootstrap  # noqa: F401  (adds project root to sys.path)
from _bootstrap import PROJECT_ROOT

from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products

from src.config_loader import load_config
from src.plaid_client import get_plaid_client

ENV_PATH = PROJECT_ROOT / ".env"
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
INDEX_PATH = PROJECT_ROOT / "index.html"


# --- small helpers --------------------------------------------------------

def _say(msg=""):
    print(msg, flush=True)


def _step(n, msg):
    _say(f"\n\033[1m[{n}]\033[0m {msg}")


def _ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or (default or "")


def _confirm(prompt, default=True):
    d = "Y/n" if default else "y/N"
    val = input(f"{prompt} ({d}): ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes")


def _die(msg):
    _say(f"\n\033[31mAborted:\033[0m {msg}")
    sys.exit(1)


def _backup(path: Path):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = path.with_suffix(path.suffix + f".{stamp}.bak")
    shutil.copy2(path, bak)
    return bak


def _slug(name: str) -> str:
    """Turn a friendly name into an ENV-safe uppercase slug."""
    s = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").upper()
    return s or "ACCOUNT"


# --- .env editing ---------------------------------------------------------

def _env_var_names():
    if not ENV_PATH.exists():
        return set()
    names = set()
    for line in ENV_PATH.read_text().splitlines():
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if m:
            names.add(m.group(1))
    return names


def _write_env_var(var: str, value: str):
    """Append (or update) VAR=value in .env, preserving everything else."""
    _backup(ENV_PATH)
    lines = ENV_PATH.read_text().splitlines()
    pattern = re.compile(rf"^\s*{re.escape(var)}\s*=")
    replaced = False
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = f"{var}={value}"
            replaced = True
            break
    if not replaced:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"{var}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n")
    return replaced


# --- config.yaml editing --------------------------------------------------

def _build_yaml_entry(name, env_var, account_ids, enabled):
    lines = [
        f'  - name: "{name}"',
        f"    access_token_env: {env_var}",
    ]
    if account_ids:
        ids = ", ".join(f'"{a}"' for a in account_ids)
        lines.append(f"    account_ids: [{ids}]")
    lines.append(f"    enabled: {'true' if enabled else 'false'}")
    return "\n".join(lines)


def _append_account(entry: str):
    """Insert a new account entry into the accounts: block of config.yaml.

    Text-based so comments in config.yaml are preserved. The entry is placed
    just before the first top-level key that follows accounts: (e.g. settings:).
    """
    _backup(CONFIG_PATH)
    text = CONFIG_PATH.read_text()
    lines = text.splitlines()

    # Locate the 'accounts:' top-level key.
    acc_idx = next(
        (i for i, l in enumerate(lines) if re.match(r"^accounts:\s*$", l)), None
    )
    if acc_idx is None:
        _die("Could not find an 'accounts:' block in config.yaml.")

    # Find the next top-level key (column 0, non-comment) after accounts:.
    insert_at = len(lines)
    for i in range(acc_idx + 1, len(lines)):
        if re.match(r"^[A-Za-z0-9_]+:", lines[i]):
            insert_at = i
            break

    # Back up over trailing blank lines so the entry sits with its siblings.
    j = insert_at
    while j - 1 > acc_idx and lines[j - 1].strip() == "":
        j -= 1

    block = ["", *entry.splitlines()]
    new_lines = lines[:j] + block + lines[j:]
    CONFIG_PATH.write_text("\n".join(new_lines) + "\n")


# --- index.html link-token injection --------------------------------------

def _inject_link_token(token: str):
    text = INDEX_PATH.read_text()
    new_text, n = re.subn(
        r"(const\s+linkToken\s*=\s*)'[^']*'",
        rf"\g<1>'{token}'",
        text,
    )
    if n == 0:
        _die("Could not find the linkToken line in index.html to update.")
    INDEX_PATH.write_text(new_text)


# --- main flow ------------------------------------------------------------

def main():
    _say("\033[1m=== Add a new account ===\033[0m")
    _say("This links one bank login end-to-end. Have the bank's credentials ready.")

    try:
        config = load_config()
    except Exception as e:
        _die(f"Could not load config/.env: {e}")

    client = get_plaid_client(config)

    # 1. Link token -------------------------------------------------------
    _step(1, "Generating a Plaid link token...")
    try:
        resp = client.link_token_create(
            LinkTokenCreateRequest(
                products=[Products("transactions")],
                client_name="My Personal Tracker",
                country_codes=[CountryCode("US")],
                language="en",
                user=LinkTokenCreateRequestUser(client_user_id="user_123"),
            )
        )
        link_token = resp["link_token"]
    except Exception as e:
        _die(f"link_token_create failed: {e}")
    _say(f"    link token: {link_token}")

    # 2. Browser ----------------------------------------------------------
    _step(2, "Opening Plaid Link in your browser...")
    _inject_link_token(link_token)
    try:
        webbrowser.open(INDEX_PATH.as_uri())
        _say("    Log into your bank in the popup. When you see 'Success!',")
        _say("    copy the public_token from the alert box.")
    except Exception:
        _say(f"    Could not auto-open. Open this file manually: {INDEX_PATH}")

    # 3. Exchange ---------------------------------------------------------
    _step(3, "Exchanging the public_token for an access token...")
    public_token = _ask("    Paste the public_token")
    if not public_token:
        _die("No public_token provided.")
    try:
        ex = client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=public_token)
        )
        access_token = ex["access_token"]
        item_id = ex["item_id"]
    except Exception as e:
        _die(f"Token exchange failed: {e}")
    _say(f"    got access token (item_id={item_id})")

    # 4. Name + env var ---------------------------------------------------
    _step(4, "Naming the account...")
    name = _ask("    Friendly name (e.g. Chase Freedom)")
    if not name:
        _die("A name is required.")
    env_var = f"PLAID_TOKEN_{_slug(name)}"
    existing = _env_var_names()
    while env_var in existing:
        _say(f"    {env_var} already exists in .env.")
        alt = _ask("    Choose a different env var name", f"{env_var}_2")
        env_var = alt.upper()

    # 5. Card selection ---------------------------------------------------
    _step(5, "Looking up the cards under this login...")
    account_ids = []
    try:
        acc = client.accounts_get(AccountsGetRequest(access_token=access_token))
        cards = list(acc["accounts"])
    except Exception as e:
        cards = []
        _say(f"    (could not list accounts: {e} — will track the whole login)")

    if len(cards) == 1:
        _say(f"    One account found: {cards[0].name}. Tracking it.")
        account_ids = []
    elif cards:
        for i, a in enumerate(cards, 1):
            official = getattr(a, "official_name", None) or ""
            extra = f" ({official})" if official else ""
            _say(
                f"    {i}. {a.name}{extra} — {a.type}/{a.subtype} "
                f"mask={a.mask}"
            )
        _say("    Enter the numbers to track (comma-separated), or blank for ALL.")
        pick = _ask("    Track which")
        if pick:
            try:
                idxs = [int(x) for x in re.split(r"[,\s]+", pick) if x]
                account_ids = [cards[i - 1].account_id for i in idxs]
            except (ValueError, IndexError):
                _die("Invalid selection.")

    enabled = _confirm("    Enable this account now?", default=True)

    # 6. Write files ------------------------------------------------------
    _step(6, "Saving to .env and config.yaml...")
    updated = _write_env_var(env_var, access_token)
    _say(f"    .env: {'updated' if updated else 'added'} {env_var}")
    entry = _build_yaml_entry(name, env_var, account_ids, enabled)
    _append_account(entry)
    _say("    config.yaml: added ->")
    for l in entry.splitlines():
        _say(f"        {l}")

    # 7. Test -------------------------------------------------------------
    _say()
    if _confirm("Run a quick test fetch now?", default=True):
        _step(7, "Running: python -m src.main --window today --no-notify")
        subprocess.run(
            [sys.executable, "-m", "src.main", "--window", "today", "--no-notify"],
            cwd=str(PROJECT_ROOT),
        )

    _say(f"\n\033[32mDone.\033[0m '{name}' is linked. The next 5 PM run and the "
         "dashboard will include it automatically.")


if __name__ == "__main__":
    main()
