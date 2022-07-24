import abc


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


class KeyNotFoundError(Exception):
    pass
