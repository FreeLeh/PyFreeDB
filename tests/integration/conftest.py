import pytest
import os
from typing import Dict
import dataclasses
import json
import time


@dataclasses.dataclass
class Config:
    spreadsheet_id: str
    service_account_info: Dict[str, str]
    sheet_name: str


@pytest.fixture
def config() -> Config:
    account_info_json = os.getenv("T_SERVICE_ACCOUNT_INFO", "{}")
    ts = time.time_ns()

    return Config(
        spreadsheet_id=os.getenv("T_SPREADSHEET_ID", ""),
        service_account_info=json.loads(account_info_json),
        sheet_name="integration_" + str(ts),
    )
