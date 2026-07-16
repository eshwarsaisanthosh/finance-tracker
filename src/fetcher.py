# src/fetcher.py
import os
from plaid.api import plaid_api
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
from dotenv import load_dotenv
from src.config_loader import load_config

load_dotenv()

def get_plaid_client():
    config = load_config()
    # Construct the host URL dynamically based on the config
    env = config['app_settings'].get('plaid_env', 'sandbox')
    host = f'https://{env}.plaid.com'
    
    configuration = Configuration(
        host=host,
        api_key={
            'clientId': os.getenv('PLAID_CLIENT_ID'),
            'secret': os.getenv('PLAID_SECRET'),
            'plaidVersion': '2020-09-14'
        }
    )
    return plaid_api.PlaidApi(ApiClient(configuration))

def fetch_all_transactions():
    config = load_config()
    client = get_plaid_client()
    all_data = {}

    for account in config['accounts']:
        if account.get('include_in_total'):
            request = TransactionsSyncRequest(
                access_token=account['id'],
            )
            response = client.transactions_sync(request)
            all_data[account['name']] = response.added
            
    return all_data