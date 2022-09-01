import abc


class Codec(abc.ABC):
    def encode(self, data: bytes) -> str:
        pass

    def decode(self, data: str) -> bytes:
        pass


class InvalidOperationError(Exception):
    """Operation is not supported"""

    pass
