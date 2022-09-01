import abc

from google.oauth2.credentials import Credentials


class GoogleAuthClient(abc.ABC):
    """An abstraction layer that represents way to authenticate with Google APIs."""

    @abc.abstractmethod
    def credentials(self) -> Credentials:
        pass
