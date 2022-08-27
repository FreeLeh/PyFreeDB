class Ordering:
    _field_name: str
    _value: str


class OrderingAsc(Ordering):
    _value = "ASC"

    def __init__(self, field_name: str):
        self._field_name = field_name


class OrderingDesc(Ordering):
    _value = "DESC"

    def __init__(self, field_name: str):
        self._field_name = field_name
