from typing import Any, Dict, Generic, Type, TypeVar
from pyfreeleh.row import models
import abc
from pyfreeleh.row.models import Model
from pyfreeleh.providers.google.sheet.base import A1CellSelector


T = TypeVar("T")


class Serializer(abc.ABC, Generic[T]):
    def deserialize(self, data: Dict[str, Any]) -> T:
        pass

    def serialize(self, obj: T) -> Dict[str, Any]:
        pass


class ModelGoogleSheetSerializer(Serializer[Model]):
    def __init__(self, model: Type[Model]):
        self._model = model

        self._col_name_by_field = self._get_col_name_mapping()
        self._field_by_col_name = {v: k for (k, v) in self._col_name_by_field.items()}

        print(self._col_name_by_field)

    def deserialize(self, data: Dict[str, Any]) -> Model:
        value_by_field = {}

        for col_name, value in data.items():
            field_name = self._field_by_col_name[col_name]
            value_by_field[field_name] = value

        return self._model(**value_by_field)

    def serialize(self, obj: Model) -> Dict[str, Any]:
        data = {}

        for field, col_name in self._col_name_by_field.items():
            value = getattr(obj, field)
            if value is models.NotSet:
                continue

            data[col_name] = value

        return data

    def _get_col_name_mapping(self) -> Dict[str, str]:
        result = {}
        for idx, field in enumerate(self._model._fields.values()):
            result[field._field_name] = str(A1CellSelector.from_rc(column=idx + 1))

        return result
