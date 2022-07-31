from typing import Callable

import pytest

from pyfreeleh.kv.base import KeyNotFoundError
from pyfreeleh.kv.gsheet import GoogleSheetKVStore

from .conftest import IntegrationTestConfig


def test_gsheet_kv_store_append_mode_integration(config: IntegrationTestConfig):
    kv_store = GoogleSheetKVStore(
        config.auth_client,
        spreadsheet_id=config.spreadsheet_id,
        sheet_name="kv_append_mode",
        mode=GoogleSheetKVStore.APPEND_ONLY_MODE,
    )
    kv_store_integration(kv_store)


def test_gsheet_kv_store_default_mode_integration(config: IntegrationTestConfig):
    kv_store = GoogleSheetKVStore(
        config.auth_client,
        spreadsheet_id=config.spreadsheet_id,
        sheet_name="kv_default",
        mode=GoogleSheetKVStore.DEFAULT_MODE,
    )
    kv_store_integration(kv_store)


def kv_store_integration(kv_store: GoogleSheetKVStore):
    ensure_key_not_found(lambda: kv_store.get("k1"))

    # Set k1 with some value.
    kv_store.set("k1", "some value".encode("utf-8"))

    # ...and we expect to receive the same value.
    value = kv_store.get("k1")
    assert value == b"some value"

    # Delete k1.
    kv_store.delete("k1")

    # ...and we expect k1 to be missing now.
    ensure_key_not_found(lambda: kv_store.get("k1"))


def ensure_key_not_found(f: Callable[[str], bytes]):
    try:
        f()
        pytest.fail("should trigger except clause")
    except KeyNotFoundError:
        pass
