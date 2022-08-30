import json
from datetime import datetime, timedelta
from typing import Any

import pytest

from pyfreedb.providers.google.auth.oauth import OAuth2GoogleAuthClient

user_secret_info = {
    "token": "token",
    "refresh_token": "refresh_token",
    "token_uri": "token_uri",
    "client_id": "client_id",
    "client_secret": "client_secret",
    "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
    "expiry": (datetime.now() + timedelta(hours=1)).isoformat(),
}


def test_oauth2_file_integration(tmp_path: Any) -> None:
    # Instantiate from user info dict should not raise exception.
    OAuth2GoogleAuthClient.from_authorized_user_info(user_secret_info)

    # Instantiate from user file should not raise exception.
    f = tmp_path / "user_secret.json"
    f.write_text(json.dumps(user_secret_info))
    OAuth2GoogleAuthClient.from_authorized_user_file(str(f))

    # Should provide the client credentials if the authorised user file is not found.
    try:
        OAuth2GoogleAuthClient.from_authorized_user_file("invalid_file.json")
        pytest.fail("should raise ValueError")
    except ValueError as e:
        pass
