import dataclasses
import inspect
from typing import Any, Dict, Generic, Optional, Type, TypeVar, Union, cast


# To differentiate between fields that are not set and Null
class NotSet:
    pass


T = TypeVar("T")


class Field(Generic[T]):
    _typ: Type[T]
    _column_name: Optional[str]
    _field_name: str

    def __init__(self, column_name: Optional[str] = None) -> None:
        self._column_name = column_name

    def __set_name__(self, _: Any, name: str) -> None:
        self._field_name = name

        if self._column_name is None:
            self._column_name = name

    def __get__(self, obj: Any, _: Any) -> Optional[T]:
        value = getattr(obj._data, self._field_name)
        return cast(Optional[T], value)

    def __set__(self, obj: Any, value: Optional[T]) -> None:
        return setattr(obj._data, self._field_name, value)


class IntegerField(Field[int]):
    _typ = int


class FloatField(Field[float]):
    _typ = float


class BoolField(Field[bool]):
    _typ = bool


class StringField(Field[str]):
    _typ = str


class PrimaryKeyField(IntegerField):
    pass


class meta(type):
    def __new__(cls, name: str, bases: Any, dct: Any) -> "meta":
        new_cls = super().__new__(cls, name, bases, dct)

        # In python3.7 dict ordering is guaranteed based on the insert time.
        fields = {}
        for base in bases:
            try:
                fields.update(base._fields)
            except AttributeError:
                pass

        for field_name, value in dct.items():
            if not isinstance(value, Field):
                continue

            if isinstance(value, PrimaryKeyField) ^ (field_name == "rid"):
                raise Exception("can only have 1 PrimaryKeyField and the name must be _rid")

            fields[field_name] = value

        setattr(new_cls, "_fields", fields)

        # Internally, we will store the actual data in a dataclass so that we don't need to deal with the
        # how to store the data.
        dataclasses_fields = []
        for (field_name, field) in fields.items():
            if field_name == "rid":
                field_type = Union[field._typ, None, NotSet]
            else:
                field_type = Union[field._typ, NotSet]

            value = dataclasses.field(default=NotSet)
            dataclasses_fields.append((field_name, cast(type, field_type), value))
        data_klass = dataclasses.make_dataclass(name, dataclasses_fields)

        # TODO(fata.nugraha): figure out how to make the __init__ annotation is the same as dataclasses' __init__
        # annotation to improve the developer experience.
        def init(self: Any, *args: Any, **kwargs: Any) -> None:
            self._data = data_klass(*args, **kwargs)

        def repr(self: Any) -> str:
            return str(self._data)

        def eq(self: Any, other: Any) -> bool:
            return new_cls is other.__class__ and self._data == other._data

        setattr(new_cls, "__init__", init)
        setattr(new_cls, "__repr__", repr)
        setattr(new_cls, "__eq__", eq)

        new_cls.__doc__ = data_klass.__name__ + str(inspect.signature(data_klass)).replace(" -> None", "")
        return new_cls


class Model(metaclass=meta):
    _fields: Dict[str, Field]
    _data: Any

    rid = PrimaryKeyField(column_name="_rid")

    def asdict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self._data)
        return {k: v for k, v in d.items() if v is not NotSet}
