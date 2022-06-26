from .base import Codec

class BasicCodec(Codec):
    def encode(self, data: bytes) -> str:
        # Add 1 dummy character so that it's impossible for the user to insert #N/A 
        # to the sheet (which we rely on to determine whether the key is exists or not).
        return " "+data.decode("utf-8")
    
    def decode(self, data: str) -> bytes:
        return data[1:].encode("utf-8")
