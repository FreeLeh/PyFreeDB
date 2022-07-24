import string
from dataclasses import dataclass
from typing import Any, List, Optional


def to_a1_column(col_idx: int) -> str:
    result = []
    while col_idx:
        cur = (col_idx - 1) % 26
        result.append(string.ascii_uppercase[cur])
        col_idx = (col_idx - cur) // 26

    return "".join(result[::-1])


@dataclass
class A1CellSelector:
    # "" means we select the entire column.
    column: str = ""
    # 0 means we select the entire row.
    row: int = 0

    @classmethod
    def from_rc(cls, column: str = "", row: int = 0) -> "A1CellSelector":
        column_str = ""
        if column:
            column_str = to_a1_column(column)

        return cls(row=row, column=column_str)

    @classmethod
    def from_notation(cls, notation: str) -> "A1CellSelector":
        column, row = notation, ""

        for i, c in enumerate(notation):
            if c.isdigit():
                column = notation[:i]
                row = notation[i:]
                break

        return cls(row=row, column=column)

    @property
    def notation(self) -> str:
        row = ""
        if self.row:
            row = str(self.row)

        return self.column + row


@dataclass
class A1Range:
    sheet_name: str = ""
    # If both start and end equals to None, means that the range refers to all cells.
    start: Optional[A1CellSelector] = None
    end: Optional[A1CellSelector] = None

    @classmethod
    def from_notation(cls, notation: str) -> "A1Range":
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
                start = A1CellSelector.from_notation(start_raw)
                end = A1CellSelector.from_notation(end_raw)
            else:
                start = A1CellSelector(notation)
                end = A1CellSelector(notation)

        return cls(sheet_name=sheet_name, start=start, end=end)

    @property
    def notation(self) -> str:
        notation = []
        if self.sheet_name:
            notation.append(self.sheet_name)

        if self.start and self.end:
            notation.append(self.start.notation + ":" + self.end.notation)

        return "!".join(notation)


@dataclass
class InsertRowsResult:
    updated_range: A1Range
    updated_rows: int
    updated_columns: int
    updated_cells: int
    inserted_values: List[List[Any]]


@dataclass
class UpdateRowsResult:
    updated_range: A1Range
    updated_rows: int
    updated_columns: int
    updated_cells: int
    updated_values: List[List[Any]]


@dataclass
class BatchUpdateRowsRequest:
    range: A1Range
    values: List[List[Any]]
