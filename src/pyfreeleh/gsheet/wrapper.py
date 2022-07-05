class GoogleSheetAPI:
    def __init__(self, auth_client: GoogleAuthClient):
        service = build("sheets", "v4", credentials=auth_client.credentials())
        self._api = service.spreadsheets().values()
