from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2 import service_account

from .base import GoogleAuthClient


class ServiceAccountGoogleAuthClient(GoogleAuthClient):
    def __init__(self, creds: service_account.Credentials, populate_token: bool = True) -> None:
        """Initialise auth client instance to perform authentication using Service Account.

        Client is recommended to not instantiate this class directly, use `from_service_account_info` and
        `from_service_account_file` constructor instead.
        """

        # Token will not be populated if we don't call refresh.
        if populate_token:
            creds.refresh(Request())

        self._creds = creds

    @classmethod
    def from_service_account_info(
        cls,
        service_account_info: Dict[str, str],
        scopes: Optional[List[str]] = None,
    ) -> "ServiceAccountGoogleAuthClient":
        """Initialise the auth client using the provided service account dict.

        Args:
            service_account_info: The service account info in dict form.
            scopes: List of permitted operation by the authentication info.

        Returns:
            ServiceAccountGoogleAuthClient: The auth client instance.
        """
        creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
        return cls(creds)

    @classmethod
    def from_service_account_file(
        cls,
        filename: str,
        scopes: Optional[List[str]] = None,
    ) -> "ServiceAccountGoogleAuthClient":
        """Initialise the auth client by reading the service account info from a file.

        Args:
            filename: The path to file that contains the service account info.
            scopes: List of permitted operation by the authentication info.

        Returns:
            ServiceAccountGoogleAuthClient: The auth client instance.
        """
        creds = service_account.Credentials.from_service_account_file(filename, scopes=scopes)
        return cls(creds)

    def credentials(self) -> service_account.Credentials:
        """Returns the authenticated Google credentials.

        Returns:
            google.oauth2.service_account.Credentials: The authenticated Google credentials.
        """
        return self._creds
