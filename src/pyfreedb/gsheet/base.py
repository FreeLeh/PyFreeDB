import abc
import dataclasses
from typing import List, Optional

from google.oauth2.credentials import Credentials


@dataclasses.dataclass
class MutationResult:
    range: str
    values: List[List[str]]


class GoogleAuthClient(abc.ABC):
    @abc.abstractmethod
    def credentials(self) -> Credentials:
        raise NotImplementedError


class SheetAPI(abc.ABC):
    @abc.abstractmethod
    def append(
        self,
        spreadsheet_id: str,
        range: str,
        values: List[List[str]],
        overwrite: Optional[bool] = False,
    ) -> MutationResult:
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, spreadsheet_id: str, range: str, values: List[List[str]]) -> MutationResult:
        raise NotImplementedError

    @abc.abstractmethod
    def clear(self, spreadsheet_id: str, range: str) -> None:
        raise NotImplementedError
