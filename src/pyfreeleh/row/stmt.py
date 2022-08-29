from typing import Any, Dict, Generic, List, TypeVar

from pyfreeleh.providers.google.sheet.base import A1CellSelector, A1Range, BatchUpdateRowsRequest
from pyfreeleh.providers.google.sheet.wrapper import GoogleSheetWrapper
from pyfreeleh.row.base import Ordering
from pyfreeleh.row.models import Model
from pyfreeleh.row.query_builder import GoogleSheetQueryBuilder
from pyfreeleh.row.serializers import FieldColumnMapper, Serializer

T = TypeVar("T", bound=Model)


def map_orderings(mapper: FieldColumnMapper, orderings: List[Ordering]) -> List[Ordering]:
    mapped_orderings = []
    for order in orderings:
        col_name = mapper.to_column(order._field_name)
        mapped_ordering = order.copy()
        mapped_ordering._field_name = col_name
        mapped_orderings.append(mapped_ordering)

    return mapped_orderings


def map_conditions(mapper: FieldColumnMapper, condition: str) -> str:
    for column, field in mapper.field_by_col().items():
        condition = condition.replace(field, column)
    return condition


class CountStmt:
    def __init__(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        wrapper: GoogleSheetWrapper,
        mapper: FieldColumnMapper,
    ):
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._wrapper = wrapper
        self._mapper = mapper

        self._query = GoogleSheetQueryBuilder()

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
        mapped_conditions = map_conditions(self._mapper, condition)
        self._query.where(mapped_conditions, *args)
        return self

    def execute(self) -> int:
        """Execute the count statement.

        Returns:
            int: number of rows that matched with the given condition.
        """
        rows = self._wrapper.query(self._spreadsheet_id, self._sheet_name, self._query.build_select(["COUNT(A)"]))
        return int(rows[0]["count-A"])


class SelectStmt(Generic[T]):
    def __init__(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        wrapper: GoogleSheetWrapper,
        serializer: Serializer[T],
        mapper: FieldColumnMapper,
        selected_columns: List[str],
    ):
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._wrapper = wrapper
        self._serializer = serializer
        self._mapper = mapper
        self._selected_columns = selected_columns

        self._query = GoogleSheetQueryBuilder()

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
        mapped_conditions = map_conditions(self._mapper, condition)
        self._query.where(mapped_conditions, *args)
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
        mapped_orderings = map_orderings(self._mapper, list(orderings))
        self._query.order_by(*mapped_orderings)
        return self

    def execute(self) -> List[T]:
        """Execute the select statement.

        Returns:
            list: list of rows that matched the given condition.
        """
        mapped_columns = []
        for col in self._selected_columns:
            mapped_columns.append(self._mapper.to_column(col))

        if "A" not in mapped_columns:
            mapped_columns.insert(0, "A")

        rows = self._wrapper.query(self._spreadsheet_id, self._sheet_name, self._query.build_select(mapped_columns))

        results = []
        for row in rows:
            results.append(self._serializer.deserialize(row))

        return results


class InsertStmt(Generic[T]):
    def __init__(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        wrapper: GoogleSheetWrapper,
        serializer: Serializer[T],
        rows: List[T],
    ):
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._wrapper = wrapper
        self._serializer = serializer
        self._rows = rows

        self._query = GoogleSheetQueryBuilder()

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
        raw_values = self._get_raw_values()
        result = self._wrapper.overwrite_rows(
            self._spreadsheet_id,
            A1Range.from_notation(self._sheet_name),
            raw_values,
        )

        for idx, row in enumerate(result.inserted_values):
            self._rows[idx].rid = int(row[0])

    def _get_raw_values(self) -> List[List[str]]:
        raw_values = []

        for row in self._rows:
            serialized = self._serializer.serialize(row)

            # We don't want user to set the value of PK.
            # Note that we can't do serialized["A"] = "=ROW()" because if serialized doesn't contain "A" it will be
            # put in the back when we call serialized.values().
            serialized.pop("A", None)
            raw_values.append(["=ROW()"] + list(serialized.values()))

        return raw_values


class UpdateStmt:
    def __init__(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        wrapper: GoogleSheetWrapper,
        mapper: FieldColumnMapper,
        update_values: Dict[str, str],
    ):
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._wrapper = wrapper
        self._mapper = mapper
        self._update_values = update_values

        self._query = GoogleSheetQueryBuilder()

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
        mapped_condition = map_conditions(self._mapper, condition)
        self._query.where(mapped_condition, *args)
        return self

    def execute(self) -> int:
        """Execute the update statement.

        Returns:
            int: the number of updated rows.
        """
        # ASSUMPTION: PK is in the first cell.
        affected_rows = self._wrapper.query(self._spreadsheet_id, self._sheet_name, self._query.build_select(["A"]))
        update_candidate_indices = [int(row["A"]) for row in affected_rows]

        self._update_rows(update_candidate_indices)

        return len(update_candidate_indices)

    def _update_rows(self, indices: List[int]):
        requests = []
        for row_idx in indices:
            for col_idx, col in enumerate(self._mapper._col_name_by_field):
                if col not in self._update_values:
                    continue

                cell_selector = A1CellSelector.from_rc(col_idx + 1, row_idx)
                update_range = A1Range(self._sheet_name, cell_selector, cell_selector)
                requests.append(BatchUpdateRowsRequest(update_range, [[self._update_values[col]]]))

        self._wrapper.batch_update_rows(self._spreadsheet_id, requests)


class DeleteStmt:
    def __init__(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        wrapper: GoogleSheetWrapper,
        mapper: FieldColumnMapper,
    ):
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._wrapper = wrapper
        self._mapper = mapper

        self._query = GoogleSheetQueryBuilder()

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
        mapped_condition = map_conditions(self._mapper, condition)
        self._query.where(mapped_condition, *args)
        return self

    def execute(self) -> int:
        """Execute the delete statement.

        Returns:
            int: number of rows deleted.
        """
        # ASSUMPTION: PK is in the first cell.
        affected_rows = self._wrapper.query(self._spreadsheet_id, self._sheet_name, self._query.build_select(["A"]))
        update_candidate_indices = [int(row["A"]) for row in affected_rows]

        requests = []
        for row_idx in update_candidate_indices:
            row_selector = A1CellSelector.from_rc(row=row_idx)
            requests.append(A1Range(self._sheet_name, start=row_selector, end=row_selector))

        self._wrapper.clear(self._spreadsheet_id, requests)

        return len(update_candidate_indices)
