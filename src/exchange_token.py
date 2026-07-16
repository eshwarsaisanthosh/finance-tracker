import os
import plaid
from plaid.api import plaid_api
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from dotenv import load_dotenv

# Load your credentials from the .env file
load_dotenv()

# Setup configuration
configuration = plaid.Configuration(
    host=os.getenv('PLAID_HOST'),
    api_key={
        'clientId': os.getenv('PLAID_CLIENT_ID'),
        'secret': os.getenv('PLAID_SECRET')
    }
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

# PASTE YOUR TOKEN HERE
public_token = 'public-sandbox-6111a029-5661-4c8e-93d8-beb9023fc2d1'

# Exchange the public_token for an access_token
request = ItemPublicTokenExchangeRequest(public_token=public_token)
response = client.item_public_token_exchange(request)

access_token = response['access_token']
item_id = response['item_id']

print("----------------------------------------")
print(f"SUCCESS! Your access_token is: {access_token}")
print(f"Your item_id is: {item_id}")
print("----------------------------------------")