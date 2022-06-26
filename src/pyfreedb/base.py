import abc


class Codec(abc.ABC):
    def encode(self, data: bytes) -> str:
        pass

    def decode(self, data: str) -> bytes:
        pass


class KVStore(abc.ABC):
    @abc.abstractmethod
    def get(self, key: str) -> bytes:
        return NotImplementedError

    @abc.abstractmethod
    def set(self, key: str, data: bytes) -> None:
        return NotImplementedError

    @abc.abstractmethod
    def delete(self, key: str) -> None:
        return NotImplementedError

    @abc.abstractmethod
    def close(self) -> None:
        return NotImplementedError


class KeyNotFoundError(ValueError):
    def __init__(self, key):
        self._key = key
        super().__init__()
