import logging
import time
from typing import Optional

from ..base import Codec, KeyNotFoundError, KVStore
from ..codec import BasicCodec
from .base import SheetAPI

logger = logging.getLogger(__name__)


class GoogleSheetKVStore(KVStore):
    def __init__(
        self,
        sheet_api: SheetAPI,
        spreadsheet_id: str,
        data_sheet_name: Optional[str] = "Data",
        scratchpad_sheet_name: Optional[str] = "Scratchpad",
        codec: Optional[Codec] = BasicCodec(),
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

        value = result.values[0][0]
        if value == "#N/A":
            raise KeyNotFoundError(key)

        return self._codec.decode(value)

    def set(self, key: str, data: bytes) -> None:
        ts = int(time.time() * 1000)
        value = self._codec.encode(data)
        self._sheet_api.append(
            self._spreadsheet_id,
            "{data_sheet}!A2".format(data_sheet=self._sheet_name),
            [[key, value, ts]],
        )

    def delete(self, key: str) -> None:
        self.set(key, "")

    def close(self) -> None:
        if self._scratchpad_cell:
            self._sheet_api.clear(self._spreadsheet_id, self._scratchpad_cell)
