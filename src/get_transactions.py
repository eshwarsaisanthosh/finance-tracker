import os
import datetime
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from dotenv import load_dotenv

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

# Define date range for transactions
start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).date()
end_date = datetime.datetime.now().date()

# Fetch transactions
request = TransactionsGetRequest(
    access_token=os.getenv('PLAID_ACCESS_TOKEN'),
    start_date=start_date,
    end_date=end_date
)

response = client.transactions_get(request)
transactions = response['transactions']

# Print the results
print(f"You have {len(transactions)} transactions:")
for txn in transactions:
    print(f"{txn.date} | {txn.name} | ${txn.amount}")