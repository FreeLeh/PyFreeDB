import abc

from google.oauth2.credentials import Credentials


class GoogleAuthClient(abc.ABC):
    @abc.abstractmethod
    def credentials(self) -> Credentials:
        pass


class Scopes:
    ROW_STORE = ["https://www.googleapis.com/auth/spreadsheets"]
    KV_STORE = ["https://www.googleapis.com/auth/spreadsheets"]
