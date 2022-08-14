from pyfreeleh.row.gsheet import QueryBuilder, get_a1_column_mapping


def test_query_builder():
    def new_builder() -> QueryBuilder:
        return QueryBuilder({"_rid": "A", "col_1": "B", "col_2": "C"})

    query = new_builder().build_select(["col_1", "col_2"])
    assert query == "SELECT B,C WHERE A IS NOT NULL"

    query = new_builder().limit(10).build_select(["col_1"])
    assert query == "SELECT B WHERE A IS NOT NULL LIMIT 10"

    query = new_builder().offset(10).build_select(["col_1"])
    assert query == "SELECT B WHERE A IS NOT NULL OFFSET 10"

    query = new_builder().where("col_1 == ?", "hello").build_select(["col_1"])
    assert query == 'SELECT B WHERE A IS NOT NULL AND B == "hello"'

    query = new_builder().where("col_1 == ?", "hello").limit(10).offset(5).build_select(["col_1", "col_2"])
    assert query == 'SELECT B,C WHERE A IS NOT NULL AND B == "hello" LIMIT 10 OFFSET 5'


def test_get_a1_column_mapping():
    assert get_a1_column_mapping(["a", "b", "c"]) == {"a": "A", "b": "B", "c": "C"}
    assert get_a1_column_mapping(["A"] * 26) == {"A": "Z"}
    assert get_a1_column_mapping(["A"] * 27) == {"A": "AA"}
