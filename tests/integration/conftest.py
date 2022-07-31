import dataclasses
import json
import os
import time

import pytest
from googleapiclient.discovery import build

from pyfreeleh.providers.google.auth.service_account import ServiceAccountGoogleAuthClient


@dataclasses.dataclass
class IntegrationTestConfig:
    auth_client: ServiceAccountGoogleAuthClient
    spreadsheet_id: str


@pytest.fixture(scope="session")
def auth_client() -> ServiceAccountGoogleAuthClient:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    account_info_json = os.getenv("T_SERVICE_ACCOUNT_INFO", "{}")
    return ServiceAccountGoogleAuthClient.from_service_account_info(json.loads(account_info_json), scopes=scopes)


@pytest.fixture(scope="session")
def spreadsheet(auth_client: ServiceAccountGoogleAuthClient) -> str:
    spreadsheet_id = os.getenv("T_SPREADSHEET_ID")
    if spreadsheet_id:
        yield spreadsheet_id
        return

    test_id = str(time.time_ns())
    sheet_svc = build("sheets", "v4", credentials=auth_client.credentials())
    query = sheet_svc.spreadsheets().create(body={"properties": {"title": "freeleh-integration-" + test_id}})
    resp = query.execute()

    yield resp["spreadsheetId"]

    drive_svc = build("drive", "v3", credentials=auth_client.credentials())
    drive_svc.files().delete(fileId=resp["spreadsheetId"]).execute()


@pytest.fixture(scope="session")
def config(auth_client, spreadsheet) -> IntegrationTestConfig:
    return IntegrationTestConfig(auth_client=auth_client, spreadsheet_id=spreadsheet)
