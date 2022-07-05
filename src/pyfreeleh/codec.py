from .base import Codec


class BasicCodec(Codec):
    PREFIX = "!"

    def encode(self, data: bytes) -> str:
        # Add 1 dummy character so that it's impossible for the user to insert #N/A
        # to the sheet (which we rely on to determine whether the key is exists or not).
        return self.PREFIX + data.decode("utf-8")

    def decode(self, data: str) -> bytes:
        if not data:
            raise ValueError("data can't be empty")

        if not data.startswith(self.PREFIX):
            raise ValueError("malformed data")

        return data[1:].encode("utf-8")
