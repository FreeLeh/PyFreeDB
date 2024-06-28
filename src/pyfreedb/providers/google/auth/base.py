import abc
from typing import Union

from google.oauth2 import credentials, service_account


class GoogleAuthClient(abc.ABC):
    """An abstraction layer that represents way to authenticate with Google APIs."""

    @abc.abstractmethod
    def credentials(self) -> Union[credentials.Credentials, service_account.Credentials]:
        pass
