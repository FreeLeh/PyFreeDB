import string
from dataclasses import dataclass
from typing import Any, List, Optional


def _to_a1_column(col_idx: int) -> str:
    result = []
    while col_idx:
        cur = (col_idx - 1) % 26
        result.append(string.ascii_uppercase[cur])
        col_idx = (col_idx - cur) // 26

    return "".join(result[::-1])


@dataclass
class _A1CellSelector:
    # "" means we select the entire column.
    column: str = ""
    # 0 means we select the entire row.
    row: int = 0

    @classmethod
    def from_rc(cls, column: int = 0, row: int = 0) -> "_A1CellSelector":
        column_str = ""
        if column:
            column_str = _to_a1_column(column)

        return cls(row=row, column=column_str)

    @classmethod
    def from_notation(cls, notation: str) -> "_A1CellSelector":
        column, row = notation, 0

        for i, c in enumerate(notation):
            if c.isdigit():
                column = notation[:i]
                row = int(notation[i:])
                break

        return cls(row=row, column=column)

    def __str__(self) -> str:
        row = ""
        if self.row:
            row = str(self.row)

        return self.column + row


@dataclass
class _A1Range:
    sheet_name: str = ""
    # If both start and end equals to None, means that the range refers to all cells.
    start: Optional[_A1CellSelector] = None
    end: Optional[_A1CellSelector] = None

    @classmethod
    def from_notation(cls, notation: str) -> "_A1Range":
        sheet_name = ""
        if "!" in notation:
            # notation="Sheet1!A1:B2" -> sheet_name=Sheet1
            exc_pos = notation.index("!")
            sheet_name = notation[:exc_pos]
            notation = notation[exc_pos + 1 :]
        elif ":" not in notation:
            # notation="Sheet1" -> sheet_name=Sheet1
            sheet_name = notation
            notation = ""

        start, end = None, None
        if notation != "":
            if ":" in notation:
                start_raw, end_raw = notation.split(":")
                start = _A1CellSelector.from_notation(start_raw)
                end = _A1CellSelector.from_notation(end_raw)
            else:
                start = _A1CellSelector.from_notation(notation)
                end = _A1CellSelector.from_notation(notation)

        return cls(sheet_name=sheet_name, start=start, end=end)

    def __str__(self) -> str:
        notation = []
        if self.sheet_name:
            notation.append(self.sheet_name)

        if self.start and self.end:
            notation.append(str(self.start) + ":" + str(self.end))

        return "!".join(notation)


@dataclass
class _InsertRowsResult:
    updated_range: _A1Range
    updated_rows: int
    updated_columns: int
    updated_cells: int
    inserted_values: List[List[Any]]


@dataclass
class _UpdateRowsResult:
    updated_range: _A1Range
    updated_rows: int
    updated_columns: int
    updated_cells: int
    updated_values: List[List[Any]]


@dataclass
class _BatchUpdateRowsRequest:
    range: _A1Range
    values: List[List[Any]]
