from typing import List, Optional

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

from .base import GoogleAuthClient


class ServiceAccountGoogleAuthClient(GoogleAuthClient):
    def __init__(
        self,
        filename: str,
        scopes: Optional[List[str]] = None,
    ) -> None:
        creds = service_account.Credentials.from_service_account_file(filename, scopes=scopes)
        self._creds = creds

    def credentials(self) -> Credentials:
        return self._creds
