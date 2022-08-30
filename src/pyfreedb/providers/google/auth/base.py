import abc

from google.oauth2.credentials import Credentials


class GoogleAuthClient(abc.ABC):
    @abc.abstractmethod
    def credentials(self) -> Credentials:
        pass
