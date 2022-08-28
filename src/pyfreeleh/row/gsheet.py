from typing import Any, Dict, Generic, List, Type, TypeVar

from pyfreeleh.providers.google.auth.base import GoogleAuthClient
from pyfreeleh.providers.google.sheet.base import A1CellSelector, A1Range, BatchUpdateRowsRequest
from pyfreeleh.providers.google.sheet.wrapper import GoogleSheetSession, GoogleSheetWrapper
from pyfreeleh.row.base import Ordering
from pyfreeleh.row.models import Model, PrimaryKeyField
from pyfreeleh.row.query_builder import GoogleSheetQueryBuilder
from pyfreeleh.row.serializers import FieldColumnMapper, ModelGoogleSheetSerializer, Serializer


class InvalidQuery(Exception):
    pass


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
        sheet_session: GoogleSheetSession,
        mapper: FieldColumnMapper,
    ):
        self._sheet_session = sheet_session
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
        rows = self._sheet_session.query(self._query.build_select(["COUNT(A)"]))
        return int(rows[0]["count-A"])


class SelectStmt(Generic[T]):
    def __init__(
        self,
        sheet_session: GoogleSheetSession,
        serializer: Serializer[T],
        mapper: FieldColumnMapper,
        selected_columns: List[str],
    ):
        self._sheet_session = sheet_session
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

        rows = self._sheet_session.query(self._query.build_select(mapped_columns))

        results = []
        for row in rows:
            results.append(self._serializer.deserialize(row))

        return results


class InsertStmt(Generic[T]):
    def __init__(
        self,
        sheet_session: GoogleSheetSession,
        serializer: Serializer[T],
        rows: List[T],
    ):
        self._sheet_session = sheet_session
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
        result = self._sheet_session.overwrite_rows(A1Range.from_notation(self._sheet_session.sheet_name), raw_values)

        # TODO(fata.nugraha): think about how to set rid back.
        # we should not assume rid is the primary key.
        for idx, row in enumerate(result.inserted_values):
            self._rows[idx].rid = int(row[0])

    def _get_raw_values(self) -> List[List[str]]:
        raw_values = []

        for row in self._rows:
            serialized = self._serializer.serialize(row)
            # TODO(fata.nugraha): assumption A is the pk
            serialized.pop("A", None)
            raw_values.append(["=ROW()"] + list(serialized.values()))

        return raw_values


class UpdateStmt:
    def __init__(
        self,
        sheet_session: GoogleSheetSession,
        mapper: FieldColumnMapper,
        update_values: Dict[str, str],
    ):
        self._sheet_session = sheet_session
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
        # TODO(fata.nugraha): assumption pk is in the first cell
        affected_rows = self._sheet_session.query(self._query.build_select(["A"]))
        update_candidate_indices = [int(row["A"]) for row in affected_rows]

        requests = []
        for row_idx in update_candidate_indices:
            for col_idx, col in enumerate(self._mapper._col_name_by_field):
                if col not in self._update_values:
                    continue

                cell_selector = A1CellSelector.from_rc(col_idx + 1, row_idx)
                update_range = A1Range(self._sheet_session.sheet_name, cell_selector, cell_selector)
                requests.append(BatchUpdateRowsRequest(update_range, [[self._update_values[col]]]))

        self._sheet_session.batch_update_rows(requests)
        return len(update_candidate_indices)


class DeleteStmt:
    def __init__(
        self,
        sheet_session: GoogleSheetSession,
        mapper: FieldColumnMapper,
    ):
        self._sheet_session = sheet_session
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
        # TODO(fata.nugraha): assumption pk is in the first cell
        affected_rows = self._sheet_session.query(self._query.build_select(["A"]))
        update_candidate_indices = [int(row["A"]) for row in affected_rows]

        requests = []
        for row_idx in update_candidate_indices:
            row_selector = A1CellSelector.from_rc(row=row_idx)
            requests.append(A1Range(self._sheet_session.sheet_name, start=row_selector, end=row_selector))

        self._sheet_session.clear(requests)

        return len(update_candidate_indices)


class GoogleSheetRowStore(Generic[T]):
    def __init__(
        self,
        auth_client: GoogleAuthClient,
        spreadsheet_id: str,
        sheet_name: str,
        object_klass: Type[T],
    ):
        """Initialises the store to operate on the given `sheet_name` inside the given `spreadsheet_id`.

        During initialisation, the store will create the sheet if `sheet_name` doesn't exists inside the spreadsheet
        and will update the first row to be the column headers.

        Args:
            auth_client: the credential that we're going to use to call the Google Sheet APIs.
            spreadsheet_id: the spreadsheet id that we're going to operate on.
            sheet_name: the sheet name that we're going to operate on.
            object_klass: the row model definition that represents how the data inside the sheet looks like.
        """
        if not issubclass(object_klass, Model):
            raise TypeError("object_klass must subclass Model.")

        self._sheet_name = sheet_name
        self._object_klass = object_klass

        wrapper = GoogleSheetWrapper(auth_client)
        self._sheet_session = GoogleSheetSession(wrapper, spreadsheet_id, sheet_name)
        self._ensure_headers()

        self._columns = list(object_klass._fields.keys())
        self._serializer = ModelGoogleSheetSerializer(object_klass)
        self._mapper = FieldColumnMapper(object_klass)

    def _ensure_headers(self) -> None:
        column_headers = []
        for field in self._object_klass._fields.values():
            column_headers.append(field._header_name)

        self._sheet_session.update_rows(A1Range(self._sheet_name), [column_headers])

    def select(self, *columns: str) -> SelectStmt[T]:
        """Create the select statement that will fetch the selected columns from the sheet.

        If the pasesed in `columns` is empty, all columns will be returned.

        Args:
            *columns: list of columns that we want to get.

        Returns:
            SelectStmt: the select statement that is configured to return the selected columns.
        """
        selected_columns = list(columns)
        if len(selected_columns) == 0:
            selected_columns = self._columns

        return SelectStmt(self._sheet_session, self._serializer, self._mapper, selected_columns)

    def insert(self, rows: List[T]) -> InsertStmt[T]:
        """Create the insert statement to insert given rows into the sheet.

        Args:
            rows: list of rows to be inserted.

        Returns:
            InsertStmt: the insert statement that is configured to insert the given rows.
        """
        return InsertStmt(self._sheet_session, self._serializer, rows)

    def update(self, update_value: Dict[str, Any]) -> UpdateStmt:
        """Create the update statement to update rows on the sheet with the given value.

        Args:
            update_value: map of value by the field_name.

        Returns:
            UpdateStmt: the update statement that is configured to update the affected rows with the given value.

        Examples:
            To update all the rows (assume there's 10 rows) so that column `name` equals to `"cat"`:

            >> store.update({"name": "cat"}).execute()
            10
        """
        update_value = update_value.copy()

        pk_col_name = self._get_pk_field_name()
        update_value.pop(pk_col_name, None)

        return UpdateStmt(self._sheet_session, self._mapper, update_value)

    def delete(self) -> DeleteStmt:
        """Create a delete statement to delete the affected rows.

        Returns:
            DeleteStmt: a delete statement.
        """
        return DeleteStmt(self._sheet_session, self._mapper)

    def count(self) -> CountStmt:
        """Create a count statement to count how many rows are there in the sheet.

        Returns:
            CountStmt: a count statement.

        Examples:
            To count how many rows that has `name` equals to `"cat"` (suppose that there will be 10 of them):

            >> store.count().where("name = ?", "cat").execute()
            10
        """
        return CountStmt(self._sheet_session, self._mapper)

    def _get_pk_field_name(self) -> str:
        for field in self._object_klass._fields.values():
            if isinstance(field, PrimaryKeyField):
                return field._field_name

        raise Exception("model must have exactly one PrimaryKeyField")
