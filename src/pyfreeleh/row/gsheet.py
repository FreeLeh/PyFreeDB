from ast import Delete
import functools
from enum import Enum
import json
import time
from re import A
from typing import Any, Dict, List, Optional, Tuple
import string

from isort import code
from pyparsing import col
from pyfreeleh.base import Codec, InvalidOperationError
from pyfreeleh.codec import BasicCodec
from pyfreeleh.providers.google.auth.base import GoogleAuthClient

from pyfreeleh.providers.google.sheet.base import A1Range, BatchUpdateRowsRequest, CellSelector
from pyfreeleh.providers.google.sheet.wrapper import GoogleSheetWrapper


class InvalidQuery(Exception):
    pass


class Ordering(Enum):
    ASC = "ASC"
    DESC = "DESC"


class QueryBuilder:
    WHERE_TEMPLATE = "{} IS NOT NULL AND {}"
    TS_FIELD = "_ts"

    def __init__(self, col_mapping: Dict[str, str]):
        self._where: Optional[Tuple[str, List[any]]] = None
        self._orderings: List[Tuple[str, Ordering]] = []
        self._limit: int = 0
        self._offset: int = 0

        self._col_mapping = col_mapping

    def where(self, condition, *args) -> "QueryBuilder":
        self._validate_where(condition, args)
        self._where = (condition, args)
        return self

    def _validate_where(self, cond: str, args: any) -> None:
        if cond.count("?") != len(args):
            raise InvalidQuery("number of placeholder and argument is not equal")

    # TODO(fata.nugraha): find better interface to do this (maybe follow django/sqlalchemy style?).
    def _build_where(self) -> str:
        if not self._where:
            return ""

        # This is not 100% foolproof. Might cause some weird issues if we have field that follows gsheet
        # column naming format e.g. A, B, etc. need to find better way.
        cond, args = self.WHERE_TEMPLATE.format(self.TS_FIELD, self._where[0]), self._where[1]
        for field, col in self._col_mapping.items():
            cond = cond.replace(field, col)

        cond_parts = cond.split("?")
        parts = cond_parts + list(args)
        parts[::2] = cond_parts
        parts[1::2] = map(self._convert_arg, list(args))
        return "where " + "".join(map(str, parts))

    def _convert_arg(self, arg):
        if isinstance(arg, str):
            return '"{}"'.format(arg)

        return arg

    def order_by(self, **kwargs: Ordering) -> "QueryBuilder":
        self._validate_order_by(kwargs)

        # Note that starting from python 3.7 the dict ordering is guaranteed to be the same as its item insertion
        # ordering.
        for k, order in kwargs.items():
            self._orderings.append((k, order))
        return self

    def _validate_order_by(self, order_map: Dict[str, Ordering]):
        for key in order_map:
            if key not in self._col_mapping:
                raise InvalidQuery("unrecognised field {}".format(key))

    def _build_order_by(self) -> str:
        if not self._orderings:
            return ""

        parts = []
        for k, order in self._orderings:
            parts.append(self._col_mapping[k] + " " + order.value)

        return "order by " + "".join(parts)

    def limit(self, limit: int) -> "QueryBuilder":
        self._validate_limit(limit)
        self._limit = limit
        return self

    def _validate_limit(self, limit: int):
        if limit < 0:
            raise InvalidQuery("limit can't be less than 0")

    def _build_limit(self) -> str:
        if not self._limit:
            return ""

        return "limit {}".format(self._limit)

    def offset(self, offset: int) -> "QueryBuilder":
        self._validate_offset(offset)
        self._offset = offset
        return self

    def _validate_offset(self, offset: int):
        if offset < 0:
            raise InvalidQuery("offset can't be less than 0")

    def _build_offset(self) -> str:
        if not self._offset:
            return ""

        return "offset {}".format(self._offset)

    def build_select(self, columns) -> str:
        cols = []
        for col in columns:
            cols.append(self._col_mapping[col])

        parts = ["select " + ",".join(cols)]
        parts.append(self._build_where())
        parts.append(self._build_order_by())
        parts.append(self._build_limit())
        parts.append(self._build_offset())

        parts = [part for part in parts if part]
        return " ".join(parts)


class SelectStmt:
    def __init__(self, wrapper: GoogleSheetWrapper, spreadsheet_id: str, sheet_name: str, columns: List[str]):
        self._wrapper = wrapper
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._columns = columns

        a1_col_mapping = get_a1_column_mapping(columns)
        self._query = QueryBuilder(a1_col_mapping)
        self._col_mapping = a1_col_mapping
        self._field_by_col = {col: field for field, col in self._col_mapping.items()}

    def where(self, condition, *args) -> "SelectStmt":
        self._query.where(condition, *args)
        return self

    def limit(self, limit: int) -> "SelectStmt":
        self._query.limit(limit)
        return self

    def offset(self, offset: int) -> "SelectStmt":
        self._query.offset(offset)
        return self

    def order_by(self, **kwargs: Ordering) -> "SelectStmt":
        self._query.order_by(**kwargs)
        return self

    def execute(self) -> List[Dict[str, Any]]:
        results = []

        rows = self._wrapper.query(self._spreadsheet_id, self._sheet_name, self._query.build_select(self._columns))
        for row in rows:
            row_result = {}
            for k, v in row.items():
                row_result[self._field_by_col[k]] = v
            results.append(row_result)

        return results


class InsertStmt:
    def __init__(
        self,
        wrapper: GoogleSheetWrapper,
        spreadsheet_id: str,
        sheet_name: str,
        columns: List[str],
        rows: List[Dict[str, str]],
    ):
        self._wrapper = wrapper
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._columns = columns
        self._rows = rows

        a1_col_mapping = get_a1_column_mapping(columns)
        self._query = QueryBuilder(a1_col_mapping)
        self._col_mapping = a1_col_mapping
        self._field_by_col = {col: field for field, col in self._col_mapping.items()}

    def execute(self):
        raw_values = self._get_raw_values()
        self._wrapper.overwrite_rows(self._spreadsheet_id, A1Range.from_notation(self._sheet_name), raw_values)

    def _get_raw_values(self):
        raw_values = []
        for row in self._rows:
            raw_values.append(self._to_values_row(row))
        return raw_values

    def _to_values_row(self, row):
        result = []
        for col in self._columns:
            result.append(row.get(col, ""))
        return result

class UpdateStmt:
    INDICES_FORMULA_TEMPLATE = '=JOIN(",", ARRAYFORMULA(QUERY({{{}, ROW({})}}, "{}")))'
    ROW_IDX_FIELD = "_idx"

    def __init__(
        self,
        wrapper: GoogleSheetWrapper,
        spreadsheet_id: str,
        sheet_name: str,
        scratchpad_cell: A1Range,
        columns: List[str],
        update_values: Dict[str,str]
    ):
        self._val = update_values
        self._wrapper = wrapper
        self._sheet_name = sheet_name
        self._spreadsheet_id = spreadsheet_id
        self._scratchpad_cell = scratchpad_cell
        self._columns = columns

        c1_col_mapping = get_c1_column_mapping(self._columns + [self.ROW_IDX_FIELD])
        self._query = QueryBuilder(c1_col_mapping)

    def where(self, condition, *args) -> "UpdateStmt":
        self._query.where(condition, *args)
        return self

    def execute(self):
        location = A1Range(self._sheet_name, CellSelector(to_a1_column(1), "2"), CellSelector(to_a1_column(len(self._columns)))).notation
        query = self._query.build_select([self.ROW_IDX_FIELD]).replace('"', '""')
        formula = self.INDICES_FORMULA_TEMPLATE.format(location, location, query)

        result = self._wrapper.update_rows(self._spreadsheet_id, self._scratchpad_cell, [[formula]])
        update_candidate_indices = [int(idx) for idx in result.updated_values[0][0].split(",") if idx]

        requests = []
        for row_idx in update_candidate_indices:
            for col_idx, col in enumerate(self._columns):
                if col not in self._val:
                    continue

                requests.append(
                    BatchUpdateRowsRequest(
                        A1Range(
                            self._sheet_name,
                            CellSelector(to_a1_column(col_idx+1), str(row_idx)),
                            CellSelector(to_a1_column(col_idx+1), str(row_idx))
                        ),
                        [[self._val[col]]]
                    )
                )

        # print(requests)
        self._wrapper.batch_update_rows(self._spreadsheet_id, requests)


class DeleteStmt:
    INDICES_FORMULA_TEMPLATE = '=JOIN(",", ARRAYFORMULA(QUERY({{{}, ROW({})}}, "{}")))'
    ROW_IDX_FIELD = "_idx"

    def __init__(
        self,
        wrapper: GoogleSheetWrapper,
        spreadsheet_id: str,
        sheet_name: str,
        scratchpad_cell: A1Range,
        columns: List[str],
    ):
        self._wrapper = wrapper
        self._sheet_name = sheet_name
        self._spreadsheet_id = spreadsheet_id
        self._scratchpad_cell = scratchpad_cell
        self._columns = columns

        c1_col_mapping = get_c1_column_mapping(self._columns + [self.ROW_IDX_FIELD])
        self._query = QueryBuilder(c1_col_mapping)

    def where(self, condition, *args) -> "DeleteStmt":
        self._query.where(condition, *args)
        return self

    def execute(self):
        location = A1Range(self._sheet_name, CellSelector(to_a1_column(1), "2"), CellSelector(to_a1_column(len(self._columns)))).notation
        query = self._query.build_select([self.ROW_IDX_FIELD]).replace('"', '""')
        formula = self.INDICES_FORMULA_TEMPLATE.format(location, location, query)

        result = self._wrapper.update_rows(self._spreadsheet_id, self._scratchpad_cell, [[formula]])
        update_candidate_indices = [int(idx) for idx in result.updated_values[0][0].split(",") if idx]

        requests = []
        for row_idx in update_candidate_indices:
            requests.append(
                A1Range(
                    self._sheet_name,
                    CellSelector("", str(row_idx)),
                    CellSelector("", str(row_idx))
                ),
            )

        self._wrapper.clear(self._spreadsheet_id, requests)



class GoogleSheetRowStore:
    SCRATCHPAD_BOOKED_VALUE = "BOOKED"
    SCRATCHPAD_SUFFIX = "_scratch"
    TS_COLUMN_NAME = "_ts"

    def __init__(self,
        auth_client: GoogleAuthClient,
        spreadsheet_id: str,
        sheet_name: str,
        columns: List[str],
        codec: Codec = BasicCodec(),
    ):
        self._auth_client = auth_client
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._columns = columns + [self.TS_COLUMN_NAME]
        self._codec = codec

        self._scratchpad_name = sheet_name + self.SCRATCHPAD_SUFFIX
        self._wrapper = GoogleSheetWrapper(auth_client)
        self._ensure_sheet()
        self._ensure_headers()
        self._book_scratchpad_cell()
        self._closed = False

    def _book_scratchpad_cell(self) -> None:
        result = self._wrapper.overwrite_rows(
            self._spreadsheet_id,
            A1Range.from_notation(self._scratchpad_name),
            [[self.SCRATCHPAD_BOOKED_VALUE]],
        )

        self._scratchpad_cell = result.updated_range

    def _ensure_sheet(self) -> None:
        try:
            self._wrapper.create_sheet(self._spreadsheet_id, self._sheet_name)
        except Exception:
            pass

        try:
            self._wrapper.create_sheet(self._spreadsheet_id, self._scratchpad_name)
        except Exception:
            pass

    def _ensure_headers(self) -> None:
        self._wrapper.update_rows(self._spreadsheet_id, A1Range(self._sheet_name), [self._columns])

    def select(self) -> SelectStmt:
        return SelectStmt(self._wrapper, self._spreadsheet_id, self._sheet_name, self._columns)

    def insert(self, rows: List[Dict[str, Any]]) -> InsertStmt:
        # _ts field is required to help us select non-empty rows.
        for row in rows:
            row[self.TS_COLUMN_NAME] = time.time()

        return InsertStmt(self._wrapper, self._spreadsheet_id, self._sheet_name, self._columns, rows)

    def update(self, value: Dict[str, Any]) -> UpdateStmt:
        return UpdateStmt(self._wrapper, self._spreadsheet_id, self._sheet_name, self._scratchpad_cell, self._columns, value)

    def delete(self) -> DeleteStmt:
        return DeleteStmt(self._wrapper, self._spreadsheet_id, self._sheet_name, self._scratchpad_cell, self._columns)

    def close(self) -> None:
        self._ensure_initialised()

        self._wrapper.clear(self._spreadsheet_id, [self._scratchpad_cell])
        self._closed = True

    def _ensure_initialised(self) -> None:
        if self._closed:
            raise InvalidOperationError



def get_a1_column_mapping(columns):
    result = {}
    for idx, col in enumerate(columns):
        result[col] = to_a1_column(idx+1)

    return result

def to_a1_column(col_idx: int) -> str:
    result = []
    while col_idx:
        cur = (col_idx-1) % 26
        result.append(string.ascii_uppercase[cur])
        col_idx = (col_idx-cur)//26

    return "".join(result[::-1])

def get_c1_column_mapping(columns):
    result = {}
    for idx, col in enumerate(columns):
        result[col] = "Col" + str(idx+1)
    return result
