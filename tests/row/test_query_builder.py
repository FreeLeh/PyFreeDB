from pyfreeleh.row.base import Ordering
from pyfreeleh.row.query_builder import GoogleSheetQueryBuilder


def test_query_builder() -> None:
    query = GoogleSheetQueryBuilder().build_select(["B", "C"])
    assert query == "SELECT B,C WHERE A IS NOT NULL"

    query = GoogleSheetQueryBuilder().limit(10).build_select(["B"])
    assert query == "SELECT B WHERE A IS NOT NULL LIMIT 10"

    query = GoogleSheetQueryBuilder().offset(10).build_select(["B"])
    assert query == "SELECT B WHERE A IS NOT NULL OFFSET 10"

    query = GoogleSheetQueryBuilder().order_by(Ordering.ASC("A"), Ordering.DESC("B")).build_select(["A", "B"])
    assert query == "SELECT A,B WHERE A IS NOT NULL ORDER BY A ASC, B DESC"

    query = GoogleSheetQueryBuilder().where("B == ?", "hello").build_select(["B"])
    assert query == 'SELECT B WHERE A IS NOT NULL AND B == "hello"'

    query = GoogleSheetQueryBuilder().where("B == ?", "hello").limit(10).offset(5).build_select(["B", "C"])
    assert query == 'SELECT B,C WHERE A IS NOT NULL AND B == "hello" LIMIT 10 OFFSET 5'
