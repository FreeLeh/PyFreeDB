from typing import Any, Dict, Generic, List, Type, TypeVar

from pyfreedb.providers.google.auth.base import GoogleAuthClient
from pyfreedb.providers.google.sheet.base import _A1Range
from pyfreedb.providers.google.sheet.wrapper import _GoogleSheetWrapper
from pyfreedb.row.models import Model
from pyfreedb.row.query_builder import _ColumnReplacer, _GoogleSheetQueryBuilder
from pyfreedb.row.stmt import CountStmt, DeleteStmt, InsertStmt, SelectStmt, UpdateStmt

T = TypeVar("T", bound=Model)


AUTH_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetRowStore(Generic[T]):
    """This class implements the FreeDB row store protocol."""

    _RID_COLUMN_NAME = "_rid"
    _WHERE_DEFAULT_CLAUSE = f"{_RID_COLUMN_NAME} IS NOT NULL"

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
            auth_client: The credential that we're going to use to call the Google Sheet APIs.
            spreadsheet_id: The spreadsheet id that we're going to operate on.
            sheet_name: The sheet name that we're going to operate on.
            object_cls: The row model definition that represents how the data inside the sheet looks like.
        """
        if not issubclass(object_cls, Model):
            raise TypeError("object_cls must subclass Model.")

        self._sheet_name = sheet_name
        self._object_cls = object_cls

        self._wrapper = _GoogleSheetWrapper(auth_client)
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._ensure_sheet()

        self._replacer = _ColumnReplacer(self._RID_COLUMN_NAME, object_cls)
        self._columns = list(object_cls._fields.keys())

    def _ensure_sheet(self) -> None:
        try:
            self._wrapper.create_sheet(self._spreadsheet_id, self._sheet_name)
        except Exception:
            pass

        column_headers = [self._RID_COLUMN_NAME]
        for field in self._object_cls._fields.values():
            column_headers.append(field._column_name)

        self._wrapper.update_rows(self._spreadsheet_id, _A1Range(self._sheet_name), [column_headers])

    def select(self, *columns: str) -> SelectStmt[T]:
        """Create the select statement that will fetch the selected columns from the sheet.

        If the passed in `columns` is empty, all columns will be returned.

        Args:
            *columns: List of columns that we want to get.

        Returns:
            pyfreedb.row.stmt.SelectStmt: The select statement that is configured to return the selected columns.

        Examples:
            Get rows that has name equals to `"cat"`:

            >>> store.select("name").where("name = ?", "cat").execute()
            [Person(name="cat")]
        """
        selected_columns = list(columns)
        if len(selected_columns) == 0:
            selected_columns = self._columns

        return SelectStmt(self, selected_columns)

    def insert(self, rows: List[T]) -> InsertStmt[T]:
        """Create the insert statement to insert given rows into the sheet.

        Args:
            rows: List of rows to be inserted.

        Returns:
            pyfreedb.row.stmt.InsertStmt: The insert statement that is configured to insert the given rows.

        Examples:
            Insert a row into the DB.

            >>> rows = [Person(name="cat")]
            >>> store.insert(rows).execute()
            None
        """
        return InsertStmt(self, rows)

    def update(self, update_value: Dict[str, Any]) -> UpdateStmt[T]:
        """Create the update statement to update rows on the sheet with the given value.

        Args:
            update_value: Map of value by the field name.

        Returns:
            pyfreedb.row.stmt.UpdateStmt: The update statement that is configured to update the affected rows with the
                                          given value.

        Examples:
            To update all the rows (assume there are 10 rows) so that column `name` equals to `"cat"`:

            >>> store.update({"name": "cat"}).execute()
            10
        """
        for key in update_value:
            if key not in self._object_cls._fields:
                raise ValueError(f"{key} field is not recognised.")

        return UpdateStmt(self, update_value)

    def delete(self) -> DeleteStmt[T]:
        """Create a delete statement to delete the affected rows.

        Returns:
            pyfreedb.row.stmt.DeleteStmt: A delete statement.

        Exemples:
            To delete all rows that has name equals to cat (suppose there are 10 of them):

            >>> store.delete().where("name = ?", "cat").execute()
            10
        """
        return DeleteStmt(self)

    def count(self) -> CountStmt[T]:
        """Create a count statement to count how many rows are there in the sheet.

        Returns:
            pyfreedb.row.stmt.CountStmt: A count statement.

        Examples:
            To count how many rows that has `name` equals to `"cat"` (suppose that there are 10 of them):

            >>> store.count().where("name = ?", "cat").execute()
            10
        """
        return CountStmt(self)

    def _new_query_builder(self) -> _GoogleSheetQueryBuilder:
        return _GoogleSheetQueryBuilder(self._replacer).where(self._WHERE_DEFAULT_CLAUSE)
