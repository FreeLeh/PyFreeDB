import logging
import time
from typing import Optional

from ..base import Codec, KeyNotFoundError, KVStore
from ..codec import BasicCodec
from .base import SheetAPI

logger = logging.getLogger(__name__)


class AppendOnlyGoogleSheetKVStore(KVStore):
    def __init__(
        self,
        sheet_api: SheetAPI,
        spreadsheet_id: str,
        data_sheet_name: str = "Data",
        scratchpad_sheet_name: str = "Scratchpad",
        codec: Codec = BasicCodec(),
    ):
        self._sheet_api = sheet_api
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = data_sheet_name
        self._scratchpad_sheet_name = scratchpad_sheet_name
        self._codec = codec
        self._scratchpad_cell: str = ""

    def get(self, key: str) -> bytes:
        formula = '=VLOOKUP("{key}", SORT({data_sheet}!A2:C5000000, 3, FALSE), 2, FALSE)'.format(
            data_sheet=self._sheet_name,
            key=key,
        )

        if not self._scratchpad_cell:
            cell = self._scratchpad_sheet_name + "!A1"
            result = self._sheet_api.append(self._spreadsheet_id, cell, [[formula]], overwrite=True)
            self._scratchpad_cell = result.range
        else:
            result = self._sheet_api.update(self._spreadsheet_id, self._scratchpad_cell, [[formula]])

        if not result.values:
            raise KeyNotFoundError(key)

        value = result.values[0][0]
        if value == "#N/A":
            raise KeyNotFoundError(key)

        return self._codec.decode(value)

    def set(self, key: str, data: bytes) -> None:
        value = self._codec.encode(data)
        self._set(key, value)

    def _set(self, key: str, data: str) -> None:
        ts = int(time.time() * 1000)
        self._sheet_api.append(
            self._spreadsheet_id,
            "{data_sheet}!A2".format(data_sheet=self._sheet_name),
            [[key, data, ts]],
        )

    def delete(self, key: str) -> None:
        self._set(key, "")

    def close(self) -> None:
        if self._scratchpad_cell:
            self._sheet_api.clear(self._spreadsheet_id, [self._scratchpad_cell])


class GoogleSheetKVStore(KVStore):
    def __init__(
        self,
        sheet_api: SheetAPI,
        spreadsheet_id: str,
        data_sheet_name: str = "Data",
        scratchpad_sheet_name: str = "Scratchpad",
        codec: Codec = BasicCodec(),
    ):
        self._sheet_api = sheet_api
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = data_sheet_name
        self._scratchpad_sheet_name = scratchpad_sheet_name
        self._codec = codec
        self._scratchpad_cell: str = ""

    def get(self, key: str) -> bytes:
        formula = '=VLOOKUP("{key}", {data_sheet}!A2:B5000000, 2, FALSE)'.format(
            data_sheet=self._sheet_name,
            key=key,
        )

        if not self._scratchpad_cell:
            cell = self._scratchpad_sheet_name + "!A1"
            result = self._sheet_api.append(self._spreadsheet_id, cell, [[formula]], overwrite=True)
            self._scratchpad_cell = result.range
        else:
            result = self._sheet_api.update(self._spreadsheet_id, self._scratchpad_cell, [[formula]])

        if not result.values:
            raise KeyNotFoundError(key)

        value = result.values[0][0]
        if value == "#N/A":
            raise KeyNotFoundError(key)

        return self._codec.decode(value)

    def set(self, key: str, data: bytes) -> None:
        value = self._codec.encode(data)
        self._set(key, value)

    def _set(self, key: str, data: str) -> None:
        row = self._get_key_row(key)
        if not row:
            self._sheet_api.append(
                self._spreadsheet_id,
                "{data_sheet}!A2".format(data_sheet=self._sheet_name),
                [[key, data]],
            )
        else:
            self._sheet_api.update(
                self._spreadsheet_id,
                "{data_sheet}!A{row}:B{row}".format(data_sheet=self._sheet_name, row=row),
                [[key, data]],
            )

    def _get_key_row(self, key: str) -> Optional[int]:
        formula = '=MATCH("{key}", {data_sheet}!A:A, 0)'.format(key=key, data_sheet=self._sheet_name)

        if not self._scratchpad_cell:
            cell = self._scratchpad_sheet_name + "!A1"
            result = self._sheet_api.append(self._spreadsheet_id, cell, [[formula]], overwrite=True)
            self._scratchpad_cell = result.range
        else:
            result = self._sheet_api.update(self._spreadsheet_id, self._scratchpad_cell, [[formula]])

        if not result.values:
            return None

        value = result.values[0][0]
        if value == "#N/A":
            return None

        return value

    def delete(self, key: str) -> None:
        row = self.__get_key_row(key)
        if row:
            self._sheet_api.clear(self._spreadsheet_id, [row])

    def close(self) -> None:
        if self._scratchpad_cell:
            self._sheet_api.clear(self._spreadsheet_id, self._scratchpad_cell)
