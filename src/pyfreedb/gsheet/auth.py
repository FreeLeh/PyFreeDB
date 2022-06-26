from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

from .base import GoogleAuthClient


class OAuth2GoogleAuthClient(GoogleAuthClient):
    def __init__(self, filename: str) -> None:
        self._filename = filename

    def credentials(self) -> Credentials:
        creds = Credentials.from_authorized_user_file(self._filename)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        # TODO(fata.nugraha): decide where should we spawn the authorization flow when needed.
        return creds


class ServiceAccountGoogleAuthClient(GoogleAuthClient):
    def __init__(self, filename: str) -> None:
        self._filename = filename

    def credentials(self) -> Credentials:
        return service_account.Credentials.from_service_account_file(self._filename)
