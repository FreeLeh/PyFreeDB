import os
from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .base import GoogleAuthClient


class OAuth2GoogleAuthClient(GoogleAuthClient):
    def __init__(self, creds: Credentials) -> None:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        self._creds = creds

    @classmethod
    def from_authorized_user_info(
        cls, authorized_user_info: Dict[str, str], scopes: Optional[List[str]] = None
    ) -> "OAuth2GoogleAuthClient":
        creds = Credentials.from_authorized_user_info(authorized_user_info, scopes=scopes)
        return cls(creds)

    @classmethod
    def from_authorized_user_file(
        cls,
        authorized_user_file: str,
        client_secret_filename: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> "OAuth2GoogleAuthClient":
        if os.path.exists(authorized_user_file):
            creds = Credentials.from_authorized_user_file(authorized_user_file, scopes=scopes)
            return cls(creds)

        if not client_secret_filename:
            raise ValueError("client_secret_filename must be set if authorized_user_file is not exists")

        flow = InstalledAppFlow.from_client_secrets_file(client_secret_filename, scopes=scopes)
        creds = flow.run_local_server(port=0)
        with open(authorized_user_file, "w") as f:
            f.write(creds.to_json())

        return cls(creds)

    def credentials(self) -> Credentials:
        return self._creds
