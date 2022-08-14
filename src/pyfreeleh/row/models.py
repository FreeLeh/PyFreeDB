import dataclasses
import inspect
from typing import Any, Generic, List, Optional, Tuple, Type, TypeVar, Union, cast


# To differentiate between fields that are not set and Null
class NotSet:
    pass


T = TypeVar("T")


class Field(Generic[T]):
    _typ: Type[T]
    _title: Optional[str]

    def __init__(self, title: Optional[str] = None) -> None:
        self._title = title

    def __set_name__(self, _: Any, name: str) -> None:
        self._field_name = name

    def __get__(self, obj: Any, cls: Any) -> Optional[T]:
        value = getattr(obj._data, self._field_name)
        if value is NotSet:
            # TODO(fata.nugraha): create a proper Exception for this
            raise Exception("key not set")

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


class meta(type):
    _fields: List[Tuple[str, Any]]
    _data: Any

    def __new__(cls, name: str, bases: Any, dct: Any) -> "meta":
        new_cls = super().__new__(cls, name, bases, dct)

        fields = []
        for field, value in dct.items():
            if isinstance(value, Field):
                fields.append((field, value))
        new_cls._fields = fields

        dataclasses_fields = []
        for (field_name, field) in fields:
            field_type = cast(type, Union[field._typ, None, NotSet])
            dataclasses_fields.append((field_name, field_type, dataclasses.field(default=NotSet)))
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
    pass
