from pyfreeleh.providers.google.sheet.base import A1CellSelector, A1Range


def test_cell_selector():
    assert A1CellSelector.from_notation("A") == A1CellSelector(column="A")
    assert A1CellSelector.from_notation("1") == A1CellSelector(row=1)
    assert A1CellSelector.from_notation("A1") == A1CellSelector(column="A", row=1)
    assert A1CellSelector.from_notation("AAA123") == A1CellSelector(column="AAA", row=123)


def test_a1_range_notation():
    testcases = [
        {
            "notation": "Sheet1!A1:B2",
            "expected": A1Range("Sheet1", A1CellSelector("A", 1), A1CellSelector("B", 2)),
        },
        {
            "notation": "Sheet1!A:A",
            "expected": A1Range("Sheet1", A1CellSelector(column="A"), A1CellSelector(column="A")),
        },
        {
            "notation": "Sheet1!1:2",
            "expected": A1Range("Sheet1", A1CellSelector(row=1), A1CellSelector(row=2)),
        },
        {
            "notation": "Sheet1!A5:A",
            "expected": A1Range("Sheet1", A1CellSelector(column="A", row=5), A1CellSelector(column="A")),
        },
        {
            "notation": "A1:B2",
            "expected": A1Range("", A1CellSelector("A", 1), A1CellSelector("B", 2)),
        },
        {
            "notation": "Sheet1",
            "expected": A1Range(sheet_name="Sheet1"),
        },
        {
            "notation": "'My Custom Sheet'!A:A",
            "expected": A1Range("'My Custom Sheet'", A1CellSelector(column="A"), A1CellSelector(column="A")),
        },
        {
            "notation": "'My Custom Sheet'",
            "expected": A1Range(sheet_name="'My Custom Sheet'"),
        },
        {
            "notation": "'My Custom Sheet'!A1",
            "expected": A1Range("'My Custom Sheet'", A1CellSelector("A", 1), A1CellSelector("A", 1)),
            "expected_notation": "'My Custom Sheet'!A1:A1",
        },
    ]

    for tc in testcases:
        r = A1Range.from_notation(tc["notation"])
        assert r == tc["expected"]
        assert str(r) == tc.get("expected_notation", tc["notation"])
