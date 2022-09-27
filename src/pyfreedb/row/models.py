import dataclasses
from typing import Any, Dict, Generic, Optional, Type, TypeVar, Union, cast


class NotSet:
    """A dummy class to differentiate between fields that are not set and None.

    >>> model_obj = store.select("name").excute()[0]
    >>> model_obj.name is NotSet
    False
    >>> model_obj.age is NotSet
    True
    """


T = TypeVar("T")


class _Field(Generic[T]):
    _typ: Type[T]
    _column_name: str
    _field_name: str

    def __init__(self, column_name: str = "") -> None:
        self._column_name = column_name

    def __set_name__(self, _: Any, name: str) -> None:
        self._field_name = name

        if self._column_name == "":
            self._column_name = name

    def __get__(self, obj: Any, _: Any) -> Optional[T]:
        value = getattr(obj._data, self._field_name)
        return cast(Optional[T], value)

    def __set__(self, obj: Any, value: Optional[T]) -> None:
        self._ensure_type(value)
        if value is not NotSet:
            # We need to typecast the value to field's _typ because for number types the value will be returned
            # as float by Google Sheet's API.
            value = self._typ(value)  # type: ignore [call-arg]

        return setattr(obj._data, self._field_name, value)

    def _ensure_type(self, value: Any) -> None:
        if value is None or value is NotSet:
            return

        if isinstance(value, self._typ):
            return

        raise TypeError(f"value of field {self._field_name} has the wrong type")


class _NumberField(_Field[T]):
    def _ensure_type(self, value: Any) -> None:
        if value is None or value is NotSet:
            return

        if not isinstance(value, (int, float)):
            raise TypeError(f"value of field {self._field_name} has the wrong type")

        if isinstance(value, int) and not _is_ieee754_safe_integer(value):
            raise ValueError("f{value} can't be exactly stored as number. Use string instead to avoid precision loss.")


class IntegerField(_NumberField[int]):
    """A field for integer number values."""

    _typ = int


class FloatField(_NumberField[float]):
    """A field for storing floating point number values."""

    _typ = float


class BoolField(_Field[bool]):
    """A field for storing boolean values."""

    _typ = bool


class StringField(_Field[str]):
    """A field for storing string values."""

    _typ = str


class _Meta(type):
    def __new__(cls, name: str, bases: Any, dct: Any) -> "_Meta":
        new_cls = super().__new__(cls, name, bases, dct)

        # In python3.7 dict ordering is guaranteed based on the insert time.
        fields = {}
        for base in bases:
            try:
                fields.update(base._fields)
            except AttributeError:
                pass

        for field_name, value in dct.items():
            if not isinstance(value, _Field):
                continue

            fields[field_name] = value

        setattr(new_cls, "_fields", fields)

        # Internally, we will store the actual data in a dataclass so that we don't need to deal with the details of
        # how to store the data.
        dataclasses_fields = []
        for (field_name, field) in fields.items():
            value = dataclasses.field(default=NotSet)
            dataclasses_fields.append((field_name, cast(type, Union[field._typ, NotSet]), value))

        data_cls = dataclasses.make_dataclass(name, dataclasses_fields)

        # Ideally we should make make the __init__ annotation is the same as dataclasses' __init__
        # annotation to improve the developer experience.
        def init(self: Any, *args: Any, **kwargs: Any) -> None:
            self._data = data_cls(*args, **kwargs)
            self._validate_type()

        def repr(self: Any) -> str:
            return str(self._data)

        def eq(self: Any, other: Any) -> bool:
            return new_cls is other.__class__ and self._data == other._data

        setattr(new_cls, "__init__", init)
        setattr(new_cls, "__repr__", repr)
        setattr(new_cls, "__eq__", eq)

        return new_cls


class Model(metaclass=_Meta):
    """Base class of model class to be used by GoogleSheetRowStore.

    Client should not use this class directly, inherit this class to define your own model instead.

    >>> class Person(Model):
    ...     name = StringField()
    ...     age = IntegerField()
    """

    _fields: Dict[str, Union[IntegerField, FloatField, BoolField, StringField]]

    def _validate_type(self) -> None:
        for field in self._fields:
            # Trigger the validation by reassigning the value to itself.
            setattr(self, field, getattr(self, field))


def _is_ieee754_safe_integer(value: int) -> bool:
    return value == int(float(value))


__pydoc__ = {}
__pydoc__["StringField"] = StringField.__doc__
