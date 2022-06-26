import time
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ..base import Codec, KeyNotFoundError, KVStore
from ..codec import BasicCodec
from .base import GoogleAuthClient, MutationResult, SheetAPI


class OAuth2GoogleAuthClient(GoogleAuthClient):
    def __init__(self, filename: str) -> None:
        self._filename = filename
    
    def credentials(self) -> Credentials:
        creds = Credentials.from_authorized_user_file(self._filename)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        # TODO(fata.nugraha): decide where should we spawn the authorization flow when needed.
        return creds

class ServiceAccountGoogleAuthClient(GoogleAuthClient):
    def __init__(self, filename: str) -> None:
        self._filename = filename

    def credentials(self) -> Credentials:
        return service_account.Credentials.from_service_account_file(self._filename)        


class GoogleSheetAPI(SheetAPI):
    def __init__(self, auth_client: GoogleAuthClient):
        service = build('sheets', 'v4', credentials=auth_client.credentials())
        self._api = service.spreadsheets().values()
    
    def append(
        self, 
        spreadsheet_id: str, 
        range: str, 
        values: List[List[str]], 
        overwrite: Optional[bool] = False
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

        return MutationResult(range=result["updates"]["updatedRange"], values=result["updates"]["updatedData"]["values"])
    
    def update(
        self,
        spreadsheet_id: str,
        range: str,
        values: List[List[str]]
    ) -> MutationResult:
        result = self._api.update(
            spreadsheetId=spreadsheet_id, 
            range=range, 
            body={"values": values},
            valueInputOption="USER_ENTERED",
            includeValuesInResponse="true",
            responseValueRenderOption="FORMATTED_VALUE",
        ).execute()

        return MutationResult(range=result["updatedRange"], values=result["updatedData"]["values"])
    
    def clear(self, spreadsheet_id: str, range: str) -> None:
        self._api.clear(spreadsheetId=spreadsheet_id, range=range).execute()


class GoogleSheetKVStore(KVStore):
    def __init__(
        self, 
        sheet_api: SheetAPI, 
        spreadsheet_id: str, 
        data_sheet_name: Optional[str] = "Data",
        scratchpad_sheet_name: Optional[str] = "Scratchpad",
        codec: Optional[Codec] = BasicCodec(),
    ):
        self._sheet_api = sheet_api
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = data_sheet_name
        self._scratchpad_sheet_name = scratchpad_sheet_name
        self._codec = codec
        self._scratchpad_cell : str = ""

    def get(self, key: str) -> bytes:
        formula = "=VLOOKUP(\"{key}\", SORT({data_sheet}!A2:C5000000, 3, FALSE), 2, FALSE)".format(data_sheet=self._sheet_name, key=key)

        if not self._scratchpad_cell:
            cell = self._scratchpad_sheet_name+"!A1"            
            result = self._sheet_api.append(self._spreadsheet_id, cell, [[formula]], overwrite=True)
            self._scratchpad_cell = result.range
        else:
            result = self._sheet_api.update(self._spreadsheet_id, self._scratchpad_cell, [[formula]])
        
        value = result.values[0][0]
        if value == "#N/A":
            raise KeyNotFoundError(key)

        return self._codec.decode(value)

    def set(self, key: str, data: bytes) -> None:
        ts = int(time.time() * 1000)
        value = self._codec.encode(data)
        self._sheet_api.append(self._spreadsheet_id, "{data_sheet}!A2".format(data_sheet=self._sheet_name), [[key, value, ts]])
    
    def delete(self, key: str) -> None:
        self.set(key, "")

    def close(self) -> None:
        if self._scratchpad_cell:
            self._sheet_api.clear(self._spreadsheet_id, self._scratchpad_cell)
