"""One-time setup: create a Plaid Link token to launch Plaid Link in a browser."""
import _bootstrap  # noqa: F401  (adds project root to sys.path)

from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products

from src.plaid_client import get_plaid_client


def main():
    client = get_plaid_client()
    request = LinkTokenCreateRequest(
        products=[Products("transactions")],
        client_name="My Personal Tracker",
        country_codes=[CountryCode("US")],
        language="en",
        user=LinkTokenCreateRequestUser(client_user_id="user_123"),
    )
    try:
        response = client.link_token_create(request)
        print(f"Success! Your link_token is: {response['link_token']}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
