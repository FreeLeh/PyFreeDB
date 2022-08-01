import abc


class Codec(abc.ABC):
    def encode(self, data: bytes) -> str:
        pass

    def decode(self, data: str) -> bytes:
        pass


class InvalidOperationError(Exception):
    pass


# Please raise an issue when this happens.
class InternalError(Exception):
    pass
