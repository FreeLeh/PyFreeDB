from typing import Any, Dict, Generic, List, Type, TypeVar

from pyfreeleh.providers.google.sheet.base import A1CellSelector, A1Range, BatchUpdateRowsRequest
from pyfreeleh.providers.google.sheet.wrapper import GoogleSheetWrapper
from pyfreeleh.row.base import Ordering
from pyfreeleh.row.models import Model
from pyfreeleh.row.query_builder import ColumnReplacer, GoogleSheetQueryBuilder

T = TypeVar("T", bound=Model)


class CountStmt:
    def __init__(self, spreadsheet_id: str, sheet_name: str, wrapper: GoogleSheetWrapper, replacer: ColumnReplacer):
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._wrapper = wrapper

        self._query = GoogleSheetQueryBuilder(replacer)

    def where(self, condition: str, *args: Any) -> "CountStmt":
        """Filter the rows that we're going to count.

        The given `condition` will be used as the WHERE clause on the final query. You can use `"?"` placeholder
        inside the condition and will be replaced with the actual value given in the `*args` variadic parameter
        based on their appearance order.

        Args:
            condition: conditions of the data that we're going to get.
            *args: list of arguments that will be used to fill in the placeholders in the given `condition`.

        Returns:
            CountStmt: the count statement with the given WHERE condition applied.

        Examples:
            To apply "WHERE age > 10" filter on the select statement:

            >> store.count().where("age > ?", 10).execute()
            10
        """
        self._query.where(condition, *args)
        return self

    def execute(self) -> int:
        """Execute the count statement.

        Returns:
            int: number of rows that matched with the given condition.
        """
        rows = self._wrapper.query(self._spreadsheet_id, self._sheet_name, self._query.build_select(["COUNT(A)"]))
        return int(rows[0][0])


class SelectStmt(Generic[T]):
    def __init__(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        wrapper: GoogleSheetWrapper,
        object_cls: Type[T],
        replacer: ColumnReplacer,
        selected_columns: List[str],
    ):
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._wrapper = wrapper
        self._object_cls = object_cls
        self._selected_columns = selected_columns

        self._query = GoogleSheetQueryBuilder(replacer)

    def where(self, condition: str, *args: Any) -> "SelectStmt[T]":
        """Filter the rows that we're going to get.

        The given `condition` will be used as the WHERE clause on the final query. You can use `"?"` placeholder
        inside the condition and will be replaced with the actual value given in the `*args` variadic parameter
        based on their appearance ordering.

        Args:
            condition: conditions of the data that we're going to get.
            *args: list of arguments that will be used to fill in the placeholders in the given `condition`.

        Returns:
            SelectStmt: the select statement with the given WHERE condition applied.

        Examples:
            To apply "WHERE age > 10" filter on the select statement:

            >> len(store.select().where("age > ?", 10).execute())
            10
        """
        self._query.where(condition, *args)
        return self

    def limit(self, limit: int) -> "SelectStmt[T]":
        """Defines the maximum number of rows that we're going to return.

        Args:
            limit: limit that we want to apply.

        Returns:
            SelectStatement: select statement with the limit applied.
        """
        self._query.limit(limit)
        return self

    def offset(self, offset: int) -> "SelectStmt[T]":
        """Defines the offset of the returned rows.

        Args:
            offset: offset that we want to apply.

        Returns:
            SelectStatement: select statement with the offset applied.
        """
        self._query.offset(offset)
        return self

    def order_by(self, *orderings: Ordering) -> "SelectStmt[T]":
        """Defines the column ordering of the returned rows.

        Args:
            *orderings: the column ordering that we want to apply.

        Returns:
            SelectStatement: select statement with the column ordering applied.
        """
        self._query.order_by(*orderings)
        return self

    def execute(self) -> List[T]:
        """Execute the select statement.

        Returns:
            list: list of rows that matched the given condition.
        """
        rows = self._wrapper.query(
            self._spreadsheet_id,
            self._sheet_name,
            self._query.build_select(self._selected_columns),
        )

        results = []
        for row in rows:
            print(row)
            raw = {}
            for idx, col in enumerate(self._selected_columns):
                raw[col] = row[idx]

            results.append(self._object_cls(**raw))

        return results


class InsertStmt(Generic[T]):
    def __init__(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        wrapper: GoogleSheetWrapper,
        rows: List[T],
    ):
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._wrapper = wrapper
        self._rows = rows

    def execute(self) -> None:
        """Execute the insert statement.

        After a successful insert, all of the `rid` field of the passed in `rows` will be updated.

        Examples:
            Insert a row.

            >> row = Row(name="cat")
            >> store.insert([row]).execute()
            >> row.rid
            2
        """
        self._wrapper.overwrite_rows(
            self._spreadsheet_id,
            A1Range.from_notation(self._sheet_name),
            self._get_raw_values(),
        )

    def _get_raw_values(self) -> List[List[str]]:
        raw_values = []

        for row in self._rows:
            raw = ["=ROW()"]
            for field_name in row._fields:
                raw.append(getattr(row, field_name))

            raw_values.append(raw)

        return raw_values


class UpdateStmt:
    def __init__(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        wrapper: GoogleSheetWrapper,
        replacer: ColumnReplacer,
        object_cls: Type[Model],
        update_values: Dict[str, str],
    ):
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._wrapper = wrapper
        self._object_cls = object_cls
        self._update_values = update_values

        self._query = GoogleSheetQueryBuilder(replacer)

    def where(self, condition: str, *args: Any) -> "UpdateStmt":
        """Filter the rows that we're going to update.

        The given `condition` will be used as the WHERE clause on the final query. You can use `"?"` placeholder
        inside the condition and will be replaced with the actual value given in the `*args` variadic parameter
        based on their appearance ordering.

        Args:
            condition: conditions of the data that we're going to update.
            *args: list of arguments that will be used to fill in the placeholders in the given `condition`.

        Returns:
            UpdateStmt: the delete statement with the given WHERE condition applied.

        Examples:
            To apply "WHERE age > 10" filter on the update statement:

            >> store.update({"name": "cat"}).where("age > ?", 10).execute()
            10
        """
        self._query.where(condition, *args)
        return self

    def execute(self) -> int:
        """Execute the update statement.

        Returns:
            int: the number of updated rows.
        """
        # ASSUMPTION: PK is in the first cell.
        affected_rows = self._wrapper.query(self._spreadsheet_id, self._sheet_name, self._query.build_select(["A"]))
        update_candidate_indices = [int(row[0]) for row in affected_rows]

        self._update_rows(update_candidate_indices)

        return len(update_candidate_indices)

    def _update_rows(self, indices: List[int]):
        requests = []
        for row_idx in indices:
            for col_idx, col in enumerate(self._object_cls._fields.keys()):
                if col not in self._update_values:
                    continue

                cell_selector = A1CellSelector.from_rc(col_idx + 2, row_idx)
                update_range = A1Range(self._sheet_name, cell_selector, cell_selector)
                requests.append(BatchUpdateRowsRequest(update_range, [[self._update_values[col]]]))

        self._wrapper.batch_update_rows(self._spreadsheet_id, requests)


class DeleteStmt:
    def __init__(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        wrapper: GoogleSheetWrapper,
        replacer: ColumnReplacer,
    ):
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._wrapper = wrapper

        self._query = GoogleSheetQueryBuilder(replacer)

    def where(self, condition: str, *args: Any) -> "DeleteStmt":
        """Filter the rows that we're going to delete.

        The given `condition` will be used as the WHERE clause on the final query. You can use `"?"` placeholder
        inside the condition and will be replaced with the actual value given in the `*args` variadic parameter
        based on their appearance ordering.

        Args:
            condition: conditions of the data that we're going to delete.
            *args: list of arguments that will be used to fill in the placeholders in the given `condition`.

        Returns:
            DeleteStmt: the delete statement with the given where condition applied.

        Examples:
            To apply "WHERE age > 10" filter on the delete statement:

            >> store.delete().where("age > ?", 10).execute()
            10
        """
        self._query.where(condition, *args)
        return self

    def execute(self) -> int:
        """Execute the delete statement.

        Returns:
            int: number of rows deleted.
        """
        # ASSUMPTION: PK is in the first cell.
        affected_rows = self._wrapper.query(self._spreadsheet_id, self._sheet_name, self._query.build_select(["A"]))
        update_candidate_indices = [int(row[0]) for row in affected_rows]

        requests = []
        for row_idx in update_candidate_indices:
            row_selector = A1CellSelector.from_rc(row=row_idx)
            requests.append(A1Range(self._sheet_name, start=row_selector, end=row_selector))

        self._wrapper.clear(self._spreadsheet_id, requests)

        return len(update_candidate_indices)
