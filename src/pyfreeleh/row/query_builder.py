from typing import Any, List, Optional, Tuple

from .base import Ordering


class InvalidQuery(Exception):
    pass


class GoogleSheetQueryBuilder:
    def __init__(self) -> None:
        self._where: Optional[Tuple[str, Tuple[Any, ...]]] = None
        self._orderings: List[Ordering] = []
        self._limit: int = 0
        self._offset: int = 0

    def where(self, condition: str, *args: Any) -> "GoogleSheetQueryBuilder":
        self._validate_where(condition, args)
        self._where = (condition, args)
        return self

    def _validate_where(self, cond: str, args: Any) -> None:
        if cond.count("?") != len(args):
            raise InvalidQuery("number of placeholder and argument is not equal")

    def _build_where(self) -> str:
        # Assumption, the first field is always the PK field.
        # TODO(fata.nugraha): update the model to reflect this.
        query = "WHERE A IS NOT NULL"

        where = self._where
        if not where:
            return query

        stmt, args = where
        query = query + " AND " + stmt

        query_parts = query.split("?")
        parts = query_parts + list(args)
        parts[::2] = query_parts
        parts[1::2] = map(self._convert_arg, list(args))
        return "".join(map(str, parts))

    # TODO(fata.nugraha): is this necessary? can't recall what is this.
    def _convert_arg(self, arg: Any) -> Any:
        if isinstance(arg, str):
            return '"{}"'.format(arg)

        return arg

    def order_by(self, *args: Ordering) -> "GoogleSheetQueryBuilder":
        for order in args:
            self._orderings.append(order)

        return self

    def _build_order_by(self) -> str:
        if not self._orderings:
            return ""

        parts = []
        for order in self._orderings:
            parts.append(order._field_name + " " + order._value)

        return "ORDER BY " + ", ".join(parts)

    def limit(self, limit: int) -> "GoogleSheetQueryBuilder":
        self._validate_limit(limit)
        self._limit = limit
        return self

    def _validate_limit(self, limit: int) -> None:
        if limit < 0:
            raise InvalidQuery("limit can't be less than 0")

    def _build_limit(self) -> str:
        if not self._limit:
            return ""

        return "LIMIT {}".format(self._limit)

    def offset(self, offset: int) -> "GoogleSheetQueryBuilder":
        self._validate_offset(offset)
        self._offset = offset
        return self

    def _validate_offset(self, offset: int) -> None:
        if offset < 0:
            raise InvalidQuery("offset can't be less than 0")

    def _build_offset(self) -> str:
        if not self._offset:
            return ""

        return "OFFSET {}".format(self._offset)

    def build_select(self, columns: List[str]) -> str:
        parts = ["SELECT " + ",".join(columns)]
        parts.append(self._build_where())
        parts.append(self._build_order_by())
        parts.append(self._build_limit())
        parts.append(self._build_offset())

        parts = [part for part in parts if part]
        return " ".join(parts)
