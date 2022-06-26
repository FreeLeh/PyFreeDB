import abc


class Codec(abc.ABC):
    def encode(self, data: bytes) -> str:
        pass

    def decode(self, data: str) -> bytes:
        pass


class KVStore(abc.ABC):
    @abc.abstractmethod
    def get(self, key: str) -> bytes:
        pass

    @abc.abstractmethod
    def set(self, key: str, data: bytes) -> None:
        pass

    @abc.abstractmethod
    def delete(self, key: str) -> None:
        pass

    @abc.abstractmethod
    def close(self) -> None:
        pass


class KeyNotFoundError(ValueError):
    def __init__(self, key):
        self._key = key
        super().__init__()
