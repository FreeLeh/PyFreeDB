from pyfreedb.row.base import Ordering
from pyfreedb.row.query_builder import GoogleSheetQueryBuilder


class DummyReplacer:
    def replace(self, val: str) -> str:
        return val


def test_query_builder() -> None:
    def new_query_builder() -> GoogleSheetQueryBuilder:
        return GoogleSheetQueryBuilder(DummyReplacer())

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
