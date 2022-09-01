import time
from typing import Any, Callable, List

from pyfreedb.base import Codec, InvalidOperationError
from pyfreedb.codec import BasicCodec
from pyfreedb.providers.google.auth.base import GoogleAuthClient
from pyfreedb.providers.google.sheet.base import _A1CellSelector, _A1Range
from pyfreedb.providers.google.sheet.wrapper import _GoogleSheetWrapper

from .base import KeyNotFoundError

AUTH_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetKVStore:
    """This class implements the FreeDB KV store protocol."""

    DEFAULT_MODE = 0
    """Use the KV Store with the default mode."""

    APPEND_ONLY_MODE = 1
    """Use the KV Store with the append only mode."""

    _SCRATCHPAD_SUFFIX = "_scratch"
    _SCRATCHPAD_BOOKED_VALUE = "BOOKED"
    _NA_VALUE = "#N/A"

    def __init__(
        self,
        auth_client: GoogleAuthClient,
        spreadsheet_id: str,
        sheet_name: str,
        codec: Codec = BasicCodec(),
        mode: int = DEFAULT_MODE,
    ):
        """Initialise the KV store that operates on the given `sheet_name` inside the given `spreadsheet_id`.

        During initialisation, the store will create the sheet if `sheet_name` doesn't exists inside the spreadsheet.

        Args:
            auth_client: The credential that we're going to use to call the Google Sheet APIs.
            spreadsheet_id: The spreadsheet id that we're going to operate on.
            sheet_name: The sheet name that we're going to operate on.
            codec: The codec that will be used to serialize/deserialize the value.
            mode: The KV storage strategy.
        """

        self._auth_client = auth_client
        self._spreadsheet_id = spreadsheet_id
        self._scratchpad_name = sheet_name + self._SCRATCHPAD_SUFFIX
        self._sheet_name = sheet_name
        self._codec: Codec = codec
        self._mode = mode

        self._wrapper = _GoogleSheetWrapper(auth_client)
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
            _A1Range.from_notation(self._scratchpad_name),
            [[self._SCRATCHPAD_BOOKED_VALUE]],
        )

        self._scratchpad_cell = result.updated_range

    def get(self, key: str) -> bytes:
        """Returns the value associated with the given `key`.

        Args:
            key: The key of the item that we want to get.

        Returns:
            bytes: The value associated by the given key.

        Raises:
            KeyNotFoundError: An error when the key doesn't exists.
        """
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
        """Set the value of entry associated with the given `key` with the given`value`.

        Args:
            key: The key of the entry that we want to set.
            value: The value that we want to store.
        """
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
                self._spreadsheet_id, _A1Range.from_notation(self._sheet_name), [[key, data, ts]]
            )

    def _find_key_a1range(self, key: str) -> _A1Range:
        formula = '=MATCH("{key}", {sheet_name}!A:A, 0)'.format(key=key, sheet_name=self._sheet_name)
        resp = self._wrapper.update_rows(self._spreadsheet_id, self._scratchpad_cell, [[formula]])

        row_idx = self._ensure_values(resp.updated_values)
        return _A1Range(self._sheet_name, _A1CellSelector(row=row_idx), _A1CellSelector(row=row_idx))

    def _append_only_set(self, key: str, data: str, ts: int) -> None:
        self._wrapper.insert_rows(self._spreadsheet_id, _A1Range.from_notation(self._sheet_name), [[key, data, ts]])

    def _ensure_values(self, values: List[List[Any]]) -> Any:
        if not values:
            raise KeyNotFoundError

        value = values[0][0]
        if not value or value == self._NA_VALUE:
            raise KeyNotFoundError

        return value

    def delete(self, key: str) -> None:
        """Delete the entry associated with the given `key`.

        Args:
            key: The key of the entry that we want to delete.
        """
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
        """Clean up the resources held by the current instance.

        It's recommended to call this method once you're done with it.
        """
        self._ensure_initialised()

        self._wrapper.clear(self._spreadsheet_id, [self._scratchpad_cell])
        self._closed = True

    def _ensure_initialised(self) -> None:
        if self._closed:
            raise InvalidOperationError
