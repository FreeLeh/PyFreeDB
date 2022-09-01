import abc


class KeyNotFoundError(Exception):
    """Will be raised if the key is not found in the store."""

    pass
