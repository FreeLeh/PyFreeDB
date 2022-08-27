import abc
from typing import Any, Dict, Generic, Type, TypeVar

from pyfreeleh.providers.google.sheet.base import A1CellSelector
from pyfreeleh.row import models
from pyfreeleh.row.models import Model

T = TypeVar("T", bound=Model)


class Serializer(abc.ABC, Generic[T]):
    def deserialize(self, data: Dict[str, Any]) -> T:
        pass

    def serialize(self, obj: T) -> Dict[str, Any]:
        pass


class FieldColumnMapper:
    def __init__(self, model: Type[Model]):
        self._model = model

        self._col_name_by_field = self._get_col_name_mapping()
        self._field_by_col_name = {v: k for (k, v) in self._col_name_by_field.items()}

    def to_column(self, field: str) -> str:
        return self._col_name_by_field[field]

    def to_field(self, column: str) -> str:
        return self._field_by_col_name[column]

    def column(self, idx: int) -> str:
        for i, column in enumerate(self._field_by_col_name.keys()):
            if i == idx:
                return column

        raise ValueError

    def field(self, idx: int) -> str:
        for i, field in enumerate(self._field_by_col_name.values()):
            if i == idx:
                return field

        raise ValueError

    def col_by_field(self) -> Dict[str, str]:
        return self._col_name_by_field

    def field_by_col(self) -> Dict[str, str]:
        return self._field_by_col_name

    def _get_col_name_mapping(self) -> Dict[str, str]:
        result = {}
        for idx, field in enumerate(self._model._fields.values()):
            result[field._field_name] = str(A1CellSelector.from_rc(column=idx + 1))

        return result


class ModelGoogleSheetSerializer(Serializer[T]):
    def __init__(self, model: Type[T]):
        self._model = model
        self._mapper = FieldColumnMapper(model)

    def deserialize(self, data: Dict[str, Any]) -> T:
        value_by_field = {}

        for col_name, value in data.items():
            field_name = self._mapper.to_field(col_name)
            value_by_field[field_name] = value

        return self._model(**value_by_field)

    def serialize(self, obj: T) -> Dict[str, Any]:
        data = {}

        for field in self._model._fields:
            value = getattr(obj, field)
            if value is models.NotSet:
                continue

            data[self._mapper.to_column(field)] = value

        return data
