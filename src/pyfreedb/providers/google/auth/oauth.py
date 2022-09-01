import os
from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .base import GoogleAuthClient


class OAuth2GoogleAuthClient(GoogleAuthClient):
    def __init__(self, creds: Credentials) -> None:
        """Initialise auth client instance to perform authentication using OAuth2.

        Client is recommended to not instantiate this class directly, use `from_authorized_user_info` and
        `from_authorized_user_file` constructor instead.
        """
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        self._creds = creds

    @classmethod
    def from_authorized_user_info(
        cls,
        authorized_user_info: Dict[str, str],
        scopes: Optional[List[str]] = None,
    ) -> "OAuth2GoogleAuthClient":
        """Initialise the auth client using the provided dict.

        Args:
            authorized_user_info: The user authentication info in dict form.
            scopes: List of permitted operation by the authentication info.

        Returns:
            OAuth2GoogleAuthClient: The auth client instance.
        """
        creds = Credentials.from_authorized_user_info(authorized_user_info, scopes=scopes)
        return cls(creds)

    @classmethod
    def from_authorized_user_file(
        cls,
        authorized_user_file: str,
        client_secret_filename: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> "OAuth2GoogleAuthClient":
        """Initialise the auth client by reading the authentication info from files.

        If the file given in `authorized_user_file` is not found we will trigger the OAuth2 authentication flow (that
        requires interaction via browser) and will save the authentication info in the given `authorized_user_file.

        Args:
            authorized_user_file: The filename of the user authentication info.
            client_secret_filename: The service secret file (obtainable from the Google Credential dashboard).
            scopes: List of permitted operation by the authentication info.

        Returns:
            OAuth2GoogleAuthClient: The auth client instance.
        """
        if os.path.exists(authorized_user_file):
            creds = Credentials.from_authorized_user_file(authorized_user_file, scopes=scopes)
            return cls(creds)

        if not client_secret_filename:
            raise ValueError("client_secret_filename must be set if authorized_user_file is not exists")

        flow = InstalledAppFlow.from_client_secrets_file(client_secret_filename, scopes=scopes)
        creds = flow.run_local_server(port=0)
        with open(authorized_user_file, "w") as user_file:
            user_file.write(creds.to_json())

        return cls(creds)

    def credentials(self) -> Credentials:
        """Returns the authenticated Google credentials.

        Returns:
            google.oauth2.credentials.Credentials: The authenticated Google credentials.
        """
        return self._creds
