"""Single source of truth for building a Plaid API client.

Every script previously duplicated this configuration block. Import
`get_plaid_client()` instead so credentials and host handling live in one place.
"""
import plaid
from plaid.api import plaid_api

from src.config_loader import load_config


def get_plaid_client(config=None):
    """Return a configured PlaidApi client.

    Pass an already-loaded config to avoid re-reading files; otherwise it is
    loaded on demand.
    """
    if config is None:
        config = load_config()

    plaid_cfg = config["plaid"]
    configuration = plaid.Configuration(
        host=plaid_cfg["host"],
        api_key={
            "clientId": plaid_cfg["client_id"],
            "secret": plaid_cfg["secret"],
            "plaidVersion": "2020-09-14",
        },
    )
    return plaid_api.PlaidApi(plaid.ApiClient(configuration))
