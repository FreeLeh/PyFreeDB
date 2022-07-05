from typing import Any, List

from googleapiclient.discovery import build

from pyfreeleh.providers.google.auth.base import GoogleAuthClient

from .base import A1Range, InsertRowsResult, UpdateRowsResult


class GoogleSheetWrapper:
    APPEND_MODE_OVERWRITE = "OVERWRITE"
    APPEND_MODE_INSERT = "INSERT_ROWS"
    MAJOR_DIMENSION_ROWS = "ROWS"

    def __init__(self, auth_client: GoogleAuthClient):
        service = build("sheets", "v4", credentials=auth_client.credentials())
        self._svc = service.spreadsheets()

    def create_spreadsheet(self, title: str) -> str:
        resp = self._svc.create(body={"properties": {"title": title}}).execute()
        return str(resp["spreadsheetId"])

    def create_sheet(self, spreadsheet_id: str, sheet_name: str) -> None:
        self._svc.batchUpdate(
            spreadsheetId=spreadsheet_id, body={"requests": {"addSheet": {"properties": {"title": sheet_name}}}}
        ).execute()

    def insert_rows(self, spreadsheet_id: str, range: A1Range, values: List[List[Any]]) -> InsertRowsResult:
        return self._insert_rows(spreadsheet_id, range, values, self.APPEND_MODE_INSERT)

    def overwrite_rows(self, spreadsheet_id: str, range: A1Range, values: List[List[Any]]) -> InsertRowsResult:
        return self._insert_rows(spreadsheet_id, range, values, self.APPEND_MODE_OVERWRITE)

    def _insert_rows(self, spreadsheet_id: str, range: A1Range, values: List[List[Any]], mode: str) -> InsertRowsResult:
        resp = (
            self._svc.values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range.notation,
                insertDataOption=mode,
                includeValuesInResponse="true",
                responseValueRenderOption="FORMATTED_VALUE",
                valueInputOption="USER_ENTERED",
                body={"values": values},
            )
            .execute()
        )

        return InsertRowsResult(
            updated_range=A1Range.from_notation(resp["updates"]["updatedData"]["range"]),
            updated_rows=resp["updates"]["updatedRows"],
            updated_columns=resp["updates"]["updatedColumns"],
            updated_cells=resp["updates"]["updatedCells"],
            inserted_values=resp["updates"]["updatedData"]["values"],
        )

    def clear(self, spreadsheet_id: str, ranges: List[A1Range]) -> None:
        self._svc.values().batchClear(
            spreadsheetId=spreadsheet_id, body={"ranges": [r.notation for r in ranges]}
        ).execute()

    def update_rows(self, spreadsheet_id: str, range: A1Range, values: List[List[Any]]) -> UpdateRowsResult:
        resp = (
            self._svc.values().update(
                spreadsheetId=spreadsheet_id,
                range=range.notation,
                includeValuesInResponse="true",
                responseValueRenderOption="FORMATTED_VALUE",
                valueInputOption="USER_ENTERED",
                body={"majorDimension": self.MAJOR_DIMENSION_ROWS, "range": range.notation, "values": values},
            )
        ).execute()

        return UpdateRowsResult(
            updated_range=A1Range.from_notation(resp["updatedRange"]),
            updated_rows=resp["updatedRows"],
            updated_columns=resp["updatedColumns"],
            updated_cells=resp["updatedCells"],
            updated_values=resp["updatedData"]["values"],
        )