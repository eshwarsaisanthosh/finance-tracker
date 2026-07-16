import os
from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products

# 1. LOAD THE .ENV FILE
# This looks for the .env file in your current folder
load_dotenv()

# 2. DEBUGGING (The most important part!)
# These print statements will show you exactly what Python sees
client_id = os.getenv('PLAID_CLIENT_ID')
secret = os.getenv('PLAID_SECRET')

print(f"DEBUG - CLIENT_ID is: '{client_id}'")
print(f"DEBUG - SECRET is: '{secret}'")

if client_id is None or secret is None:
    raise ValueError("One of your environment variables is missing! Check your .env file.")

# 3. CONFIGURE
configuration = plaid.Configuration(
    host=os.getenv('PLAID_HOST'),
    api_key={
        'clientId': client_id,
        'secret': secret
    }
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

# 4. REQUEST
request = LinkTokenCreateRequest(
    products=[Products('transactions')],
    client_name="My Personal Tracker",
    country_codes=[CountryCode('US')],
    language='en',
    user=LinkTokenCreateRequestUser(client_user_id='user_123')
)

# 5. EXECUTE
try:
    response = client.link_token_create(request)
    print(f"Success! Your link_token is: {response['link_token']}")
except Exception as e:
    print(f"An error occurred: {e}")