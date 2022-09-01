import abc


class Codec(abc.ABC):
    """Codec defines the algorithm to encode and decode data before it's stored and retrieved from Google Sheets."""

    def encode(self, _: bytes) -> str:
        pass

    def decode(self, _: str) -> bytes:
        pass


class InvalidOperationError(Exception):
    """Operation is not supported."""
