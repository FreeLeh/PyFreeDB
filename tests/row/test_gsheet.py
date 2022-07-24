from pyfreeleh.row.gsheet import get_a1_column_mapping, get_c1_column_mapping

def test_get_a1_column_mapping():
    assert get_a1_column_mapping(['a', 'b', 'c']) == {"a": "A", "b": "B", "c": "C"}
    assert get_a1_column_mapping(["A"] * 26) == {"A": "Z"}
    assert get_a1_column_mapping(["A"] * 27) == {"A": "AA"}
