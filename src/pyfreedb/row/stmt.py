from typing import TYPE_CHECKING, Any, Dict, Generic, List, TypeVar

from pyfreedb.providers.google.sheet.base import A1CellSelector, A1Range, BatchUpdateRowsRequest
from pyfreedb.row.base import Ordering
from pyfreedb.row.models import Model

if TYPE_CHECKING:
    from pyfreedb.row.gsheet import GoogleSheetRowStore

T = TypeVar("T", bound=Model)


class CountStmt(Generic[T]):
    def __init__(self, store: "GoogleSheetRowStore[T]"):
        self._store = store
        self._query = store._new_query_builder()

    def where(self, condition: str, *args: Any) -> "CountStmt[T]":
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
        self._query.where(f"{self._store.WHERE_DEFAULT_CLAUSE} AND {condition}", *args)
        return self

    def execute(self) -> int:
        """Execute the count statement.

        Returns:
            int: number of rows that matched with the given condition.
        """
        query = self._query.build_select([f"COUNT({self._store.RID_COLUMN_NAME})"])
        rows = self._store._wrapper.query(self._store._spreadsheet_id, self._store._sheet_name, query)
        return int(rows[0][0])


class SelectStmt(Generic[T]):
    def __init__(self, store: "GoogleSheetRowStore[T]", selected_columns: List[str]):
        self._store = store
        self._selected_columns = selected_columns
        self._query = store._new_query_builder()

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
        self._query.where(f"{self._store.WHERE_DEFAULT_CLAUSE} AND {condition}", *args)
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
        query = self._query.build_select(self._selected_columns)
        rows = self._store._wrapper.query(self._store._spreadsheet_id, self._store._sheet_name, query)

        results = []
        for row in rows:
            raw = {}
            for idx, col in enumerate(self._selected_columns):
                raw[col] = row[idx]

            results.append(self._store._object_cls(**raw))

        return results


class InsertStmt(Generic[T]):
    def __init__(self, store: "GoogleSheetRowStore[T]", rows: List[T]):
        self._store = store
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
        self._store._wrapper.overwrite_rows(
            self._store._spreadsheet_id,
            A1Range.from_notation(self._store._sheet_name),
            self._get_raw_values(),
        )

    def _get_raw_values(self) -> List[List[str]]:
        raw_values = []

        for row in self._rows:
            # Set _rid value according to the insert protocol.
            raw = ["=ROW()"]

            for field_name in row._fields:
                raw.append(getattr(row, field_name))

            raw_values.append(raw)

        return raw_values


class UpdateStmt(Generic[T]):
    def __init__(self, store: "GoogleSheetRowStore[T]", update_values: Dict[str, str]):
        self._store = store
        self._update_values = update_values
        self._query = store._new_query_builder()

    def where(self, condition: str, *args: Any) -> "UpdateStmt[T]":
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
        self._query.where(f"{self._store.WHERE_DEFAULT_CLAUSE} AND {condition}", *args)
        return self

    def execute(self) -> int:
        """Execute the update statement.

        Returns:
            int: the number of updated rows.
        """
        query = self._query.build_select([self._store.RID_COLUMN_NAME])
        affected_rows = self._store._wrapper.query(self._store._spreadsheet_id, self._store._sheet_name, query)
        update_candidate_indices = [int(row[0]) for row in affected_rows]

        self._update_rows(update_candidate_indices)

        return len(update_candidate_indices)

    def _update_rows(self, indices: List[int]) -> None:
        requests = []
        for row_idx in indices:
            for col_idx, col in enumerate(self._store._object_cls._fields.keys()):
                if col not in self._update_values:
                    continue

                cell_selector = A1CellSelector.from_rc(col_idx + 2, row_idx)
                update_range = A1Range(self._store._sheet_name, cell_selector, cell_selector)
                requests.append(BatchUpdateRowsRequest(update_range, [[self._update_values[col]]]))

        self._store._wrapper.batch_update_rows(self._store._spreadsheet_id, requests)


class DeleteStmt(Generic[T]):
    def __init__(self, store: "GoogleSheetRowStore[T]"):
        self._store = store
        self._query = store._new_query_builder()

    def where(self, condition: str, *args: Any) -> "DeleteStmt[T]":
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
        self._query.where(f"{self._store.WHERE_DEFAULT_CLAUSE} AND {condition}", *args)
        return self

    def execute(self) -> int:
        """Execute the delete statement.

        Returns:
            int: number of rows deleted.
        """
        query = self._query.build_select([self._store.RID_COLUMN_NAME])
        affected_rows = self._store._wrapper.query(self._store._spreadsheet_id, self._store._sheet_name, query)
        affected_row_indices = [int(row[0]) for row in affected_rows]

        self._delete_rows(affected_row_indices)
        return len(affected_row_indices)

    def _delete_rows(self, indices: List[int]) -> None:
        requests = []
        for row_idx in indices:
            row_selector = A1CellSelector.from_rc(row=row_idx)
            requests.append(A1Range(self._store._sheet_name, start=row_selector, end=row_selector))

        self._store._wrapper.clear(self._store._spreadsheet_id, requests)
