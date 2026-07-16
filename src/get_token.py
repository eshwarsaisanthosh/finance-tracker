import os
from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.products import Products

# Load your credentials from .env
load_dotenv()

def get_sandbox_token():
    print("Setting up Plaid client...")
    configuration = plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={
            'clientId': os.getenv('PLAID_CLIENT_ID'),
            'secret': os.getenv('PLAID_SECRET'),
        }
    )
    api_client = plaid.ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)

    try:
        print("1. Creating a temporary public token...")
        # ins_109508 is Plaid's standard test bank (First Platypus Bank)
        pt_request = SandboxPublicTokenCreateRequest(
            institution_id="ins_109508",
            initial_products=[Products("transactions")]
        )
        pt_response = client.sandbox_public_token_create(pt_request)
        public_token = pt_response['public_token']

        print("2. Exchanging it for a permanent access token...")
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=public_token
        )
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response['access_token']
        
        print("\n=== SUCCESS! ===")
        print(f"Your Sandbox Access Token:\n\n{access_token}\n")
        print("Copy the token above and paste it into your config.yaml file.")

    except plaid.ApiException as e:
        print(f"\nAPI Error: {e}")
        print("Check that your PLAID_CLIENT_ID and PLAID_SECRET in .env are correct.")

if __name__ == "__main__":
    get_sandbox_token()