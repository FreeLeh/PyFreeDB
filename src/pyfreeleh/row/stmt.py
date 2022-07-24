from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class InvalidQuery(Exception):
    pass


class Ordering(Enum):
    ASC = "ascending"
    DESC = "descending"


class SelectStmt:
    def __init__(self, executor, col_mapping):
        self._query = GsheetQueryBuilder(col_mapping)
        self._executor = executor

    def where(self, condition, *args) -> "SelectStmt":
        self._query.where(condition, *args)
        return self

    def limit(self, limit: int) -> "SelectStmt":
        self._query.limit(limit)
        return self

    def offset(self, offset: int) -> "SelectStmt":
        self._query.offset(offset)
        return self

    def order_by(self, **kwargs: Ordering) -> "SelectStmt":
        self._query.order_by(**kwargs)
        return self

    def execute(self) -> List[Dict[str, Any]]:
        pass


class InsertStmt:
    pass


class UpdateStmt:
    pass


class DeleteStmt:
    pass


class GsheetQueryBuilder:
    def __init__(self, col_mapping: Dict[str, str]):
        self._where: Optional[Tuple[str, List[any]]] = None
        self._orderings: List[Tuple[str, Ordering]] = []
        self._limit: int = 0
        self._offset: int = 0

        self._col_mapping = col_mapping

    def where(self, condition, *args) -> "GsheetQueryBuilder":
        self._validate_where(condition, args)
        self.wes.append((condition, args))
        return self

    def _validate_where(self, cond: str, args: any) -> None:
        if cond.count("?") != len(args):
            raise InvalidQuery("number of placeholder and argument is not equal")

    def _build_where(self) -> str:
        if not self._where:
            return ""

        cond, args = self._where
        cond_parts = cond.split("?")

        parts = cond_parts + args
        parts[::2] = cond_parts
        parts[1::2] = args
        return "where " + "".join(parts)

    def order_by(self, **kwargs: Ordering) -> "GsheetQueryBuilder":
        self._validate_order_by(kwargs)

        # Note that starting from python 3.7 the dict ordering is guaranteed to be the same as its item insertion
        # ordering.
        for k, order in kwargs.items():
            self._orderings.append((k, order))
        return self

    def _validate_order_by(self, order_map: Dict[str, Ordering]):
        for key in order_map:
            if key not in self._col_mapping:
                raise InvalidQuery("unrecognised field {}".format(key))

    def _build_order_by(self) -> str:
        if not self._orderings:
            return ""

        parts = []
        for k, order in self._orderings.items():
            parts.append(self._col_mapping[k] + " " + order.value())

        return "order by " + "".join(parts)

    def limit(self, limit: int) -> "GsheetQueryBuilder":
        self._validate_limit(limit)
        self._limit = limit
        return self

    def _validate_limit(self, limit: int):
        if limit < 0:
            raise InvalidQuery("limit can't be less than 0")

    def _build_limit(self) -> str:
        if not self._limit:
            return ""

        return "limit {}".format(self._limit)

    def offset(self, offset: int) -> "GsheetQueryBuilder":
        self._validate_offset(offset)
        self._offset = offset
        return self

    def _validate_offset(self, offset: int):
        if offset < 0:
            raise InvalidQuery("offset can't be less than 0")

    def _build_offset(self) -> str:
        if not self._offset:
            return ""

        return "offset {}".format(self.offset)

    def build(self) -> str:
        cols = list(self._col_mapping.values())
        parts = ["select " + ",".join(cols)]
        parts.append(self._build_where())
        parts.append(self._build_order_by())
        parts.append(self._build_limit())
        parts.append(self._build_offset())

        parts = [part for part in parts if part]
        return " ".join(parts)
