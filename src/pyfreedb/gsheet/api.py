import logging
from typing import List, Optional

from googleapiclient.discovery import build

from .base import GoogleAuthClient, MutationResult, SheetAPI

logger = logging.getLogger(__name__)


class GoogleSheetAPI(SheetAPI):
    def __init__(self, auth_client: GoogleAuthClient):
        service = build("sheets", "v4", credentials=auth_client.credentials())
        self._api = service.spreadsheets().values()

    def append(
        self,
        spreadsheet_id: str,
        range: str,
        values: List[List[str]],
        overwrite: Optional[bool] = False,
    ) -> MutationResult:
        insertDataOption = "INSERT_ROWS"
        if overwrite:
            insertDataOption = "OVERWRITE"

        result = self._api.append(
            spreadsheetId=spreadsheet_id,
            range=range,
            body={"values": values},
            valueInputOption="USER_ENTERED",
            includeValuesInResponse="true",
            responseValueRenderOption="FORMATTED_VALUE",
            insertDataOption=insertDataOption,
        ).execute()
        logger.debug("append result=%s", result)

        return MutationResult(
            range=result["updates"]["updatedRange"],
            values=result["updates"]["updatedData"].get("values", None),
        )

    def update(self, spreadsheet_id: str, range: str, values: List[List[str]]) -> MutationResult:
        result = self._api.update(
            spreadsheetId=spreadsheet_id,
            range=range,
            body={"values": values},
            valueInputOption="USER_ENTERED",
            includeValuesInResponse="true",
            responseValueRenderOption="FORMATTED_VALUE",
        ).execute()
        logger.debug("update result=%s", result)

        return MutationResult(range=result["updatedRange"], values=result["updatedData"].get("values", None))

    def clear(self, spreadsheet_id: str, range: str) -> None:
        result = self._api.clear(spreadsheetId=spreadsheet_id, range=range).execute()
        logger.debug("clear result=%s", result)
