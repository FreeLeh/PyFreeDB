from pyfreedb.providers.google.sheet.base import _A1CellSelector, _A1Range


def test_cell_selector() -> None:
    assert _A1CellSelector.from_notation("A") == _A1CellSelector(column="A")
    assert _A1CellSelector.from_notation("1") == _A1CellSelector(row=1)
    assert _A1CellSelector.from_notation("A1") == _A1CellSelector(column="A", row=1)
    assert _A1CellSelector.from_notation("AAA123") == _A1CellSelector(column="AAA", row=123)


def test_a1_range_notation() -> None:
    testcases = [
        {
            "notation": "Sheet1!A1:B2",
            "expected": _A1Range("Sheet1", _A1CellSelector("A", 1), _A1CellSelector("B", 2)),
        },
        {
            "notation": "Sheet1!A:A",
            "expected": _A1Range("Sheet1", _A1CellSelector(column="A"), _A1CellSelector(column="A")),
        },
        {
            "notation": "Sheet1!1:2",
            "expected": _A1Range("Sheet1", _A1CellSelector(row=1), _A1CellSelector(row=2)),
        },
        {
            "notation": "Sheet1!A5:A",
            "expected": _A1Range("Sheet1", _A1CellSelector(column="A", row=5), _A1CellSelector(column="A")),
        },
        {
            "notation": "A1:B2",
            "expected": _A1Range("", _A1CellSelector("A", 1), _A1CellSelector("B", 2)),
        },
        {
            "notation": "Sheet1",
            "expected": _A1Range(sheet_name="Sheet1"),
        },
        {
            "notation": "'My Custom Sheet'!A:A",
            "expected": _A1Range("'My Custom Sheet'", _A1CellSelector(column="A"), _A1CellSelector(column="A")),
        },
        {
            "notation": "'My Custom Sheet'",
            "expected": _A1Range(sheet_name="'My Custom Sheet'"),
        },
        {
            "notation": "'My Custom Sheet'!A1",
            "expected": _A1Range("'My Custom Sheet'", _A1CellSelector("A", 1), _A1CellSelector("A", 1)),
            "expected_notation": "'My Custom Sheet'!A1:A1",
        },
    ]

    for tc in testcases:
        r = _A1Range.from_notation(tc["notation"])
        assert r == tc["expected"]
        assert str(r) == tc.get("expected_notation", tc["notation"])
