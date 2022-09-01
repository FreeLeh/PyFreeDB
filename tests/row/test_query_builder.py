from pyfreedb.row import models
from pyfreedb.row.base import Ordering
from pyfreedb.row.query_builder import _ColumnReplacer, _GoogleSheetQueryBuilder


class DummyReplacer:
    def replace(self, val: str) -> str:
        return val


class DummyModel(models.Model):
    field1 = models.IntegerField()
    field2 = models.IntegerField()


def test_replacer() -> None:
    # Get the basics right.
    replacer = _ColumnReplacer("_rid", DummyModel)
    assert replacer.replace("_rid") == "A"
    assert replacer.replace("field1") == "B"
    assert replacer.replace("field2") == "C"

    # Can replace multiple occurences.
    assert replacer.replace("_rid field1 field2 field1") == "A B C B"


def test_query_builder_mapping() -> None:
    replacer = _ColumnReplacer("_rid", DummyModel)
    query_builder = _GoogleSheetQueryBuilder(replacer)

    query = (
        query_builder.where("field1 = ?", "field1")
        .order_by(Ordering.ASC("field1"), Ordering.DESC("field2"))
        .limit(1)
        .offset(1)
        .build_select(["_rid", "field1"])
    )

    assert query == 'SELECT A,B WHERE B = "field1" ORDER BY B ASC, C DESC LIMIT 1 OFFSET 1'


def test_query_builder() -> None:
    query = new_query_builder().build_select(["B", "C"])
    assert query == "SELECT B,C"

    query = new_query_builder().limit(10).build_select(["B"])
    assert query == "SELECT B LIMIT 10"

    query = new_query_builder().offset(10).build_select(["B"])
    assert query == "SELECT B OFFSET 10"

    query = new_query_builder().order_by(Ordering.ASC("A"), Ordering.DESC("B")).build_select(["A", "B"])
    assert query == "SELECT A,B ORDER BY A ASC, B DESC"

    query = new_query_builder().order_by(Ordering.DESC("B"), Ordering.ASC("A")).build_select(["A", "B"])
    assert query == "SELECT A,B ORDER BY B DESC, A ASC"

    query = new_query_builder().where("B == ?", "hello").build_select(["B"])
    assert query == 'SELECT B WHERE B == "hello"'

    query = new_query_builder().where("B == ?", "hello").limit(10).offset(5).build_select(["B", "C"])
    assert query == 'SELECT B,C WHERE B == "hello" LIMIT 10 OFFSET 5'


def new_query_builder() -> _GoogleSheetQueryBuilder:
    return _GoogleSheetQueryBuilder(DummyReplacer())
