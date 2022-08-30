from typing import Any, Dict, Generic, List, Type, TypeVar

from pyfreedb.providers.google.auth.base import GoogleAuthClient
from pyfreedb.providers.google.sheet.base import A1Range
from pyfreedb.providers.google.sheet.wrapper import GoogleSheetWrapper
from pyfreedb.row.models import Model
from pyfreedb.row.query_builder import ColumnReplacer, GoogleSheetQueryBuilder
from pyfreedb.row.stmt import CountStmt, DeleteStmt, InsertStmt, SelectStmt, UpdateStmt

T = TypeVar("T", bound=Model)


AUTH_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetRowStore(Generic[T]):
    RID_COLUMN_NAME = "_rid"
    WHERE_DEFAULT_CLAUSE = f"{RID_COLUMN_NAME} IS NOT NULL"

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

        self._wrapper = GoogleSheetWrapper(auth_client)
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._ensure_sheet()

        self._replacer = ColumnReplacer(self.RID_COLUMN_NAME, object_cls)
        self._columns = list(object_cls._fields.keys())

    def _ensure_sheet(self) -> None:
        try:
            self._wrapper.create_sheet(self._spreadsheet_id, self._sheet_name)
        except Exception:
            pass

        column_headers = [self.RID_COLUMN_NAME]
        for field in self._object_cls._fields.values():
            column_headers.append(field._column_name)

        self._wrapper.update_rows(self._spreadsheet_id, A1Range(self._sheet_name), [column_headers])

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

        return SelectStmt(self, selected_columns)

    def insert(self, rows: List[T]) -> InsertStmt[T]:
        """Create the insert statement to insert given rows into the sheet.

        Args:
            rows: list of rows to be inserted.

        Returns:
            InsertStmt: the insert statement that is configured to insert the given rows.
        """
        return InsertStmt(self, rows)

    def update(self, update_value: Dict[str, Any]) -> UpdateStmt[T]:
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
        for key in update_value:
            if key not in self._object_cls._fields:
                raise ValueError(f"{key} field is not recognised.")

        return UpdateStmt(self, update_value)

    def delete(self) -> DeleteStmt[T]:
        """Create a delete statement to delete the affected rows.

        Returns:
            DeleteStmt: a delete statement.
        """
        return DeleteStmt(self)

    def count(self) -> CountStmt[T]:
        """Create a count statement to count how many rows are there in the sheet.

        Returns:
            CountStmt: a count statement.

        Examples:
            To count how many rows that has `name` equals to `"cat"` (suppose that there will be 10 of them):

            >> store.count().where("name = ?", "cat").execute()
            10
        """
        return CountStmt(self)

    def _new_query_builder(self) -> GoogleSheetQueryBuilder:
        return GoogleSheetQueryBuilder(self._replacer).where(self.WHERE_DEFAULT_CLAUSE)
