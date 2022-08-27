from typing import Any, Dict, Generic, List, Mapping, Optional, Tuple, Type, TypeVar

from pyfreeleh.providers.google.auth.base import GoogleAuthClient
from pyfreeleh.providers.google.sheet.base import A1CellSelector, A1Range, BatchUpdateRowsRequest
from pyfreeleh.providers.google.sheet.wrapper import GoogleSheetSession, GoogleSheetWrapper
from pyfreeleh.row.base import Ordering, OrderingAsc, OrderingDesc
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

        if isinstance(order, OrderingAsc):
            mapped_orderings.append(OrderingAsc(col_name))
        elif isinstance(order, OrderingDesc):
            mapped_orderings.append(OrderingDesc(col_name))

    return mapped_orderings


def map_conditions(mapper: FieldColumnMapper, condition: str) -> str:
    for column, field in mapper.field_by_col().items():
        condition = condition.replace(field, column)
    return condition


class CountStmt(Generic[T]):
    def __init__(
        self,
        sheet_session: GoogleSheetSession,
    ):
        self._sheet_session = sheet_session

        self._query = GoogleSheetQueryBuilder()

    def where(self, condition: str, *args: Any) -> "SelectStmt[T]":
        mapped_conditions = map_conditions(self._mapper, condition)
        self._query.where(mapped_conditions, *args)
        return self

    def execute(self) -> int:
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
        mapped_conditions = map_conditions(self._mapper, condition)
        self._query.where(mapped_conditions, *args)
        return self

    def limit(self, limit: int) -> "SelectStmt[T]":
        self._query.limit(limit)
        return self

    def offset(self, offset: int) -> "SelectStmt[T]":
        self._query.offset(offset)
        return self

    def order_by(self, *orderings: Ordering) -> "SelectStmt[T]":
        mapped_orderings = map_orderings(self._mapper, orderings)
        self._query.order_by(*mapped_orderings)
        return self

    def execute(self) -> List[T]:
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
        mapped_condition = map_conditions(self._mapper, condition)
        self._query.where(mapped_condition, *args)
        return self

    def execute(self) -> int:
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
        mapped_condition = map_conditions(self._mapper, condition)
        self._query.where(mapped_condition, *args)
        return self

    def execute(self) -> int:
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
            column_headers.append(field._column_name)

        self._sheet_session.update_rows(A1Range(self._sheet_name), [column_headers])

    def select(self, *columns: str) -> SelectStmt[T]:
        selected_columns = list(columns)
        if len(selected_columns) == 0:
            selected_columns = self._columns

        return SelectStmt(self._sheet_session, self._serializer, self._mapper, selected_columns)

    def insert(self, rows: List[T]) -> InsertStmt:
        return InsertStmt(self._sheet_session, self._serializer, rows)

    def _get_pk_field_name(self):
        for field in self._object_klass._fields.values():
            if isinstance(field, PrimaryKeyField):
                return field._field_name

        # TODO(fata.nugraha): move this to model meta instead.
        raise Exception("model must have exactly one PrimaryKeyField")

    def update(self, update_value: Dict[str, Any]) -> UpdateStmt:
        update_value = update_value.copy()

        pk_col_name = self._get_pk_field_name()
        update_value.pop(pk_col_name, None)

        return UpdateStmt(self._sheet_session, self._mapper, update_value)

    def delete(self) -> DeleteStmt:
        return DeleteStmt(self._sheet_session, self._mapper)

    def count(self) -> CountStmt:
        return CountStmt(self._sheet_session)
