import json
from datetime import datetime, timedelta

import pytest

from pyfreeleh.google.auth.oauth import OAuth2GoogleAuthClient
from pyfreeleh.google.auth.service_account import ServiceAccountGoogleAuthClient

user_secret_info = {
    "token": "token",
    "refresh_token": "refresh_token",
    "token_uri": "token_uri",
    "client_id": "client_id",
    "client_secret": "client_secret",
    "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
    "expiry": (datetime.now() + timedelta(hours=1)).isoformat(),
}

service_account = {
    "type": "service_account",
    "project_id": "project_id",
    "private_key_id": "private_key_id",
    "private_key": """-----BEGIN RSA PRIVATE KEY-----
        MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Qu
        KUpRKfFLfRYC9AIKjbJTWit+CqvjWYzvQwECAwEAAQJAIJLixBy2qpFoS4DSmoEm
        o3qGy0t6z09AIJtH+5OeRV1be+N4cDYJKffGzDa88vQENZiRm0GRq6a+HPGQMd2k
        TQIhAKMSvzIBnni7ot/OSie2TmJLY4SwTQAevXysE2RbFDYdAiEBCUEaRQnMnbp7
        9mxDXDf6AU0cN/RPBjb9qSHDcWZHGzUCIG2Es59z8ugGrDY+pxLQnwfotadxd+Uy
        v/Ow5T0q5gIJAiEAyS4RaI9YG8EWx/2w0T67ZUVAw8eOMB6BIUg0Xcu+3okCIBOs
        /5OiPgoTdSy7bcF9IGpSE8ZgGKzgYQVZeN97YE00
        -----END RSA PRIVATE KEY-----
    """,
    "client_email": "client_email",
    "client_id": "client_id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "url",
}


def test_oauth2_file_integration(tmp_path):
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


def test_service_account_integration(tmp_path):
    f = tmp_path / "service_account.json"
    f.write_text(json.dumps(service_account))

    # Instantiate from service account file should not raise exception.
    ServiceAccountGoogleAuthClient(str(f))
