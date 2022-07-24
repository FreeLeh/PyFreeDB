import time
from typing import Any, Callable, List

from pyfreeleh.base import Codec, InvalidOperationError
from pyfreeleh.codec import BasicCodec
from pyfreeleh.providers.google.auth.base import GoogleAuthClient
from pyfreeleh.providers.google.sheet.base import A1CellSelector, A1Range
from pyfreeleh.providers.google.sheet.wrapper import GoogleSheetWrapper

from .base import KeyNotFoundError, KVStore


class GoogleSheetKVStore(KVStore):
    DEFAULT_MODE = 0
    APPEND_ONLY_MODE = 1
    SCRATCHPAD_SUFFIX = "_scratch"
    SCRATCHPAD_BOOKED_VALUE = "BOOKED"
    NA_VALUE = "#N/A"

    def __init__(
        self,
        auth_client: GoogleAuthClient,
        spreadsheet_id: str,
        sheet_name: str,
        codec: Codec = BasicCodec(),
        mode: int = DEFAULT_MODE,
    ):
        self._auth_client = auth_client
        self._spreadsheet_id = spreadsheet_id
        self._scratchpad_name = sheet_name + self.SCRATCHPAD_SUFFIX
        self._sheet_name = sheet_name
        self._codec: Codec = codec
        self._mode = mode

        self._wrapper = GoogleSheetWrapper(auth_client)
        self._ensure_sheet()
        self._book_scratchpad_cell()
        self._closed = False

    def _ensure_sheet(self) -> None:
        try:
            self._wrapper.create_sheet(self._spreadsheet_id, self._sheet_name)
        except Exception:
            pass

        try:
            self._wrapper.create_sheet(self._spreadsheet_id, self._scratchpad_name)
        except Exception:
            pass

    def _book_scratchpad_cell(self) -> None:
        result = self._wrapper.overwrite_rows(
            self._spreadsheet_id,
            A1Range.from_notation(self._scratchpad_name),
            [[self.SCRATCHPAD_BOOKED_VALUE]],
        )

        self._scratchpad_cell = result.updated_range

    def get(self, key: str) -> bytes:
        self._ensure_initialised()

        formula = self._get_formula(key)

        resp = self._wrapper.update_rows(self._spreadsheet_id, self._scratchpad_cell, [[formula]])
        value = self._ensure_values(resp.updated_values)
        return self._codec.decode(value)

    def _get_formula(self, key: str) -> str:
        if self._mode == self.DEFAULT_MODE:
            return '=VLOOKUP("{key}", {sheet_name}!A:B, 2, FALSE)'.format(sheet_name=self._sheet_name, key=key)

        if self._mode == self.APPEND_ONLY_MODE:
            return '=VLOOKUP("{key}", SORT({sheet_name}!A:C, 3, FALSE), 2, FALSE)'.format(
                sheet_name=self._sheet_name, key=key
            )

        assert False, "unrecognised mode"

    def set(self, key: str, value: bytes) -> None:
        self._ensure_initialised()

        strategy = self._get_set_strategy()

        value_enc = self._codec.encode(value)
        ts = int(time.time() * 1000)
        strategy(key, value_enc, ts)

    def _get_set_strategy(self) -> Callable[[str, str, int], None]:
        if self._mode == self.DEFAULT_MODE:
            return self._default_set

        if self._mode == self.APPEND_ONLY_MODE:
            return self._append_only_set

        assert False, "unrecognised mode"

    def _default_set(self, key: str, data: str, ts: int) -> None:
        try:
            key_range = self._find_key_a1range(key)
            self._wrapper.update_rows(self._spreadsheet_id, key_range, [[key, data, ts]])
        except KeyNotFoundError:
            self._wrapper.overwrite_rows(
                self._spreadsheet_id, A1Range.from_notation(self._sheet_name), [[key, data, ts]]
            )

    def _find_key_a1range(self, key: str) -> A1Range:
        formula = '=MATCH("{key}", {sheet_name}!A:A, 0)'.format(key=key, sheet_name=self._sheet_name)
        resp = self._wrapper.update_rows(self._spreadsheet_id, self._scratchpad_cell, [[formula]])

        row_idx = str(self._ensure_values(resp.updated_values))
        return A1Range(self._sheet_name, A1CellSelector(row=row_idx), A1CellSelector(row=row_idx))

    def _append_only_set(self, key: str, data: str, ts: int) -> None:
        self._wrapper.insert_rows(self._spreadsheet_id, A1Range.from_notation(self._sheet_name), [[key, data, ts]])

    def _ensure_values(self, values: List[List[Any]]) -> Any:
        if not values or not values[0]:
            raise KeyNotFoundError

        value = values[0][0]
        if not value or value == self.NA_VALUE:
            raise KeyNotFoundError

        return value

    def delete(self, key: str) -> None:
        self._ensure_initialised()

        if self._mode == self.DEFAULT_MODE:
            self._default_delete(key)

        if self._mode == self.APPEND_ONLY_MODE:
            self._append_only_delete(key)

    def _default_delete(self, key: str) -> None:
        try:
            r = self._find_key_a1range(key)
        except KeyNotFoundError:
            return

        self._wrapper.clear(self._spreadsheet_id, [r])

    def _append_only_delete(self, key: str) -> None:
        ts = int(time.time() * 1000)
        self._append_only_set(key, "", ts)

    def close(self) -> None:
        self._ensure_initialised()

        self._wrapper.clear(self._spreadsheet_id, [self._scratchpad_cell])
        self._closed = True

    def _ensure_initialised(self) -> None:
        if self._closed:
            raise InvalidOperationError
