import logging
from oauth2client.client import (
    flow_from_clientsecrets,
    FlowExchangeError,
    OAuth2Credentials,
    Credentials,
)
from googleapiclient.discovery import build
import httplib2
from google.auth.transport.requests import Request
import os
import pydantic
import json
import argparse
from urllib.parse import urlparse


def get_gauth_file() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gauth-file",
        type=str,
        default="./.gauth.json",
        help="Path to client secrets file",
    )
    args, _ = parser.parse_known_args()
    return args.gauth_file


CLIENTSECRETS_LOCATION = get_gauth_file()

def get_redirect_uri() -> str:
    with open(get_gauth_file(), "r") as f:
        data = json.load(f)
    return data["web"]["redirect_uris"][0]

def extract_redirect_uri_port() -> int:
    try:
        redirect_uri = get_redirect_uri()
        if not redirect_uri:
            logging.warning("Redirect URI is empty. Defaulting to port 4100.")
            return 4100

        parsed = urlparse(redirect_uri)
        if parsed.scheme not in ("http", "https"):
            logging.warning(f"Unexpected URI scheme: {parsed.scheme}. Defaulting to port 4100.")
            return 4100

        if parsed.port:
            return parsed.port

    except Exception as e:
        logging.error(f"Failed to extract port from redirect URI: {e}")

    return 4100

REDIRECT_URI = get_redirect_uri()
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/calendar"
]


class AccountInfo(pydantic.BaseModel):

    email: str
    account_type: str
    extra_info: str

    def __init__(self, email: str, account_type: str, extra_info: str = ""):
        super().__init__(email=email, account_type=account_type, extra_info=extra_info)

    def to_description(self):
        return f"""Account for email: {self.email} of type: {self.account_type}. Extra info for: {self.extra_info}"""


def get_accounts_file() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--accounts-file",
        type=str,
        default="./.accounts.json",
        help="Path to accounts configuration file",
    )
    args, _ = parser.parse_known_args()
    return args.accounts_file


def get_account_info() -> list[AccountInfo]:
    accounts_file = get_accounts_file()
    with open(accounts_file) as f:
        data = json.load(f)
        accounts = data.get("accounts", [])
        return [AccountInfo.model_validate(acc) for acc in accounts]

class GetCredentialsException(Exception):
  """Error raised when an error occurred while retrieving credentials.

  Attributes:
    authorization_url: Authorization URL to redirect the user to in order to
                       request offline access.
  """

  def __init__(self, authorization_url):
    """Construct a GetCredentialsException."""
    self.authorization_url = authorization_url


class CodeExchangeException(GetCredentialsException):
  """Error raised when a code exchange has failed."""


class NoRefreshTokenException(GetCredentialsException):
  """Error raised when no refresh token has been found."""


class NoUserIdException(Exception):
  """Error raised when no user ID could be retrieved."""


def get_credentials_dir() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--credentials-dir",
        type=str,
        default=".",
        help="Directory to store OAuth2 credentials",
    )
    args, _ = parser.parse_known_args()
    return args.credentials_dir


def _get_credential_filename(user_id: str) -> str:
    creds_dir = get_credentials_dir()
    return os.path.join(creds_dir, f".oauth2.{user_id}.json")


def get_stored_credentials(user_id: str) -> OAuth2Credentials | None:
    """Retrieved stored credentials for the provided user ID.

    Args:
    user_id: User's ID.
    Returns:
    Stored oauth2client.client.OAuth2Credentials if found, None otherwise.
    """
    try:

        cred_file_path = _get_credential_filename(user_id=user_id)
        if not os.path.exists(cred_file_path):
            logging.warning(f"No stored Oauth2 credentials yet at path: {cred_file_path}")
            return None

        with open(cred_file_path, 'r') as f:
            data = f.read()
            return Credentials.new_from_json(data)
    except Exception as e:
        logging.error(e)
        return None

    raise None


def store_credentials(credentials: OAuth2Credentials, user_id: str):
    """Store OAuth 2.0 credentials in the specified directory."""
    cred_file_path = _get_credential_filename(user_id=user_id)
    os.makedirs(os.path.dirname(cred_file_path), exist_ok=True)

    data = credentials.to_json()
    with open(cred_file_path, "w") as f:
        f.write(data)


def exchange_code(authorization_code):
    """Exchange an authorization code for OAuth 2.0 credentials.

    Args:
    authorization_code: Authorization code to exchange for OAuth 2.0
                        credentials.
    Returns:
    oauth2client.client.OAuth2Credentials instance.
    Raises:
    CodeExchangeException: an error occurred.
    """
    flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(SCOPES))
    flow.redirect_uri = REDIRECT_URI
    try:
        credentials = flow.step2_exchange(authorization_code)
        return credentials
    except FlowExchangeError as error:
        logging.error('An error occurred: %s', error)
        raise CodeExchangeException(None)


def get_user_info(credentials):
    """Send a request to the UserInfo API to retrieve the user's information.

    Args:
    credentials: oauth2client.client.OAuth2Credentials instance to authorize the
                    request.
    Returns:
    User information as a dict.
    """
    user_info_service = build(
        serviceName='oauth2', version='v2',
        http=credentials.authorize(httplib2.Http()))
    user_info = None
    try:
        user_info = user_info_service.userinfo().get().execute()
    except Exception as e:
        logging.error(f'An error occurred: {e}')
    if user_info and user_info.get('id'):
        return user_info
    else:
        raise NoUserIdException()


def get_authorization_url(email_address, state):
    """Retrieve the authorization URL.

    Args:
    email_address: User's e-mail address.
    state: State for the authorization URL.
    Returns:
    Authorization URL to redirect the user to.
    """
    flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(SCOPES), redirect_uri=REDIRECT_URI)
    flow.params['access_type'] = 'offline'
    flow.params['approval_prompt'] = 'force'
    flow.params['user_id'] = email_address
    flow.params['state'] = state
    return flow.step1_get_authorize_url(state=state)


def get_credentials(authorization_code, state):
    """Retrieve credentials using the provided authorization code.

    This function exchanges the authorization code for an access token and queries
    the UserInfo API to retrieve the user's e-mail address.
    If a refresh token has been retrieved along with an access token, it is stored
    in the application database using the user's e-mail address as key.
    If no refresh token has been retrieved, the function checks in the application
    database for one and returns it if found or raises a NoRefreshTokenException
    with the authorization URL to redirect the user to.

    Args:
    authorization_code: Authorization code to use to retrieve an access token.
    state: State to set to the authorization URL in case of error.
    Returns:
    oauth2client.client.OAuth2Credentials instance containing an access and
    refresh token.
    Raises:
    CodeExchangeError: Could not exchange the authorization code.
    NoRefreshTokenException: No refresh token could be retrieved from the
                                available sources.
    """
    email_address = ''
    try:
        credentials = exchange_code(authorization_code)
        user_info = get_user_info(credentials)
        import json
        logging.error(f"user_info: {json.dumps(user_info)}")
        email_address = user_info.get('email')

        if credentials.refresh_token is not None:
            store_credentials(credentials, user_id=email_address)
            return credentials
        else:
            credentials = get_stored_credentials(user_id=email_address)
            if credentials and credentials.refresh_token is not None:
                return credentials
    except CodeExchangeException as error:
        logging.error('An error occurred during code exchange.')
        # Drive apps should try to retrieve the user and credentials for the current
        # session.
        # If none is available, redirect the user to the authorization URL.
        error.authorization_url = get_authorization_url(email_address, state)
        raise error
    except NoUserIdException:
        logging.error('No user ID could be retrieved.')
        # No refresh token has been retrieved.
    authorization_url = get_authorization_url(email_address, state)
    raise NoRefreshTokenException(authorization_url)
