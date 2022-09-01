from .base import Codec


class BasicCodec(Codec):
    """This class performs encoding and decoding by adding an exclamation as a prefix into the raw data."""

    PREFIX = "!"

    def encode(self, data: bytes) -> str:
        """Encode performs data encoding by adding an exclamation mark in front of the data.

        Args:
            data: The raw bytes data provided by the client.

        Returns:
            str: The encoded data in string format.
        """
        # Add 1 dummy character so that it's impossible for the user to insert #N/A
        # to the sheet (which we rely on to determine whether the key is exists or not).
        return self.PREFIX + data.decode("utf-8")

    def decode(self, data: str) -> bytes:
        if not data:
            raise ValueError("data can't be empty")

        if not data.startswith(self.PREFIX):
            raise ValueError("malformed data")

        return data[1:].encode("utf-8")
