class Ordering:
    """A class to specify specific column ordering of the query result."""

    _field_name: str
    _value: str

    @classmethod
    def ASC(cls, field_name: str) -> "Ordering":
        """Specify column ordering of the query result in ascending order.

        Args:
            field_name: The column name.

        Returns:
            Ordering: The column order object.
        """
        obj = cls()
        obj._field_name = field_name
        obj._value = "ASC"
        return obj

    @classmethod
    def DESC(cls, field_name: str) -> "Ordering":
        """Specify column ordering of the query result in descending order.

        Args:
            field_name: The column name.

        Returns:
            Ordering: The column order object.
        """
        obj = cls()
        obj._field_name = field_name
        obj._value = "DESC"
        return obj

    def _copy(self) -> "Ordering":
        obj = Ordering()
        obj._field_name = self._field_name
        obj._value = self._value
        return obj


class InvalidQuery(Exception):
    """Invalid query operation"""
