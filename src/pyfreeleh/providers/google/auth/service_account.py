from typing import List, Optional, Dict

from google.auth.transport.requests import Request
from google.oauth2 import service_account

from .base import GoogleAuthClient


class ServiceAccountGoogleAuthClient(GoogleAuthClient):
    def __init__(self, creds: service_account.Credentials) -> None:
        # Token will not be populated if we don't call refresh.
        creds.refresh(Request())
        self._creds = creds

    @classmethod
    def from_service_account_info(
        cls,
        service_account_info: Dict[str, str],
        scopes: Optional[List[str]] = None,
    ) -> "ServiceAccountGoogleAuthClient":
        creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
        return cls(creds)

    @classmethod
    def from_service_account_file(
        cls,
        filename: str,
        scopes: Optional[List[str]] = None,
    ) -> "ServiceAccountGoogleAuthClient":
        creds = service_account.Credentials.from_service_account_file(filename, scopes=scopes)
        return cls(creds)

    def credentials(self) -> service_account.Credentials:
        return self._creds
