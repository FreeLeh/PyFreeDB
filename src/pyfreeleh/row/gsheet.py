from typing import Any, Dict, Generic, List, Type, TypeVar

from pyfreeleh.providers.google.auth.base import GoogleAuthClient
from pyfreeleh.providers.google.sheet.base import A1Range
from pyfreeleh.providers.google.sheet.wrapper import GoogleSheetSession, GoogleSheetWrapper
from pyfreeleh.row.models import Model, PrimaryKeyField
from pyfreeleh.row.serializers import FieldColumnMapper, ModelGoogleSheetSerializer
from pyfreeleh.row.stmt import CountStmt, DeleteStmt, InsertStmt, SelectStmt, UpdateStmt


T = TypeVar("T", bound=Model)


class GoogleSheetRowStore(Generic[T]):
    def __init__(
        self,
        auth_client: GoogleAuthClient,
        spreadsheet_id: str,
        sheet_name: str,
        object_cls: Type[T],
    ):
        """Initialise the row store that operates on the given `sheet_name` inside the given `spreadsheet_id`.

        During initialisation, the store will create the sheet if `sheet_name` doesn't exists inside the spreadsheet
        and will update the first row to be the column headers.

        Args:
            auth_client: the credential that we're going to use to call the Google Sheet APIs.
            spreadsheet_id: the spreadsheet id that we're going to operate on.
            sheet_name: the sheet name that we're going to operate on.
            object_cls: the row model definition that represents how the data inside the sheet looks like.
        """
        if not issubclass(object_cls, Model):
            raise TypeError("object_cls must subclass Model.")

        self._sheet_name = sheet_name
        self._object_cls = object_cls

        wrapper = GoogleSheetWrapper(auth_client)
        self._sheet_session = GoogleSheetSession(wrapper, spreadsheet_id, sheet_name)
        self._ensure_headers()

        self._columns = list(object_cls._fields.keys())
        self._serializer = ModelGoogleSheetSerializer(object_cls)
        self._mapper = FieldColumnMapper(object_cls)

    def _ensure_headers(self) -> None:
        column_headers = []
        for field in self._object_cls._fields.values():
            column_headers.append(field._header_name)

        self._sheet_session.update_rows(A1Range(self._sheet_name), [column_headers])

    def select(self, *columns: str) -> SelectStmt[T]:
        """Create the select statement that will fetch the selected columns from the sheet.

        If the passed in `columns` is empty, all columns will be returned.

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
        for field in self._object_cls._fields.values():
            if isinstance(field, PrimaryKeyField):
                return field._field_name

        raise Exception("model must have exactly one PrimaryKeyField")
