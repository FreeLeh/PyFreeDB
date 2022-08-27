class Ordering:
    _field_name: str
    _value: str

    @classmethod
    def ASC(cls, field_name: str) -> "Ordering":
        obj = cls()
        obj._field_name = field_name
        obj._value = "ASC"
        return obj

    @classmethod
    def DESC(cls, field_name: str) -> "Ordering":
        obj = cls()
        obj._field_name = field_name
        obj._value = "DESC"
        return obj

    def copy(self) -> "Ordering":
        obj = Ordering()
        obj._field_name = self._field_name
        obj._value = self._value
        return obj
