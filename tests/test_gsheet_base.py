from pyfreeleh.providers.google.sheet.base import A1Range, CellSelector


def test_cell_selector():
    assert CellSelector.from_notation("A") == CellSelector(column="A")
    assert CellSelector.from_notation("1") == CellSelector(row="1")
    assert CellSelector.from_notation("A1") == CellSelector(column="A", row="1")
    assert CellSelector.from_notation("AAA123") == CellSelector(column="AAA", row="123")


def test_a1_range_notation():
    testcases = [
        {
            "notation": "Sheet1!A1:B2",
            "expected": A1Range("Sheet1", CellSelector("A", "1"), CellSelector("B", "2")),
        },
        {
            "notation": "Sheet1!A:A",
            "expected": A1Range("Sheet1", CellSelector(column="A"), CellSelector(column="A")),
        },
        {
            "notation": "Sheet1!1:2",
            "expected": A1Range("Sheet1", CellSelector(row="1"), CellSelector(row="2")),
        },
        {
            "notation": "Sheet1!A5:A",
            "expected": A1Range("Sheet1", CellSelector(column="A", row="5"), CellSelector(column="A")),
        },
        {
            "notation": "A1:B2",
            "expected": A1Range("", CellSelector("A", "1"), CellSelector("B", "2")),
        },
        {
            "notation": "Sheet1",
            "expected": A1Range(sheet_name="Sheet1"),
        },
        {
            "notation": "'My Custom Sheet'!A:A",
            "expected": A1Range("'My Custom Sheet'", CellSelector(column="A"), CellSelector(column="A")),
        },
        {
            "notation": "'My Custom Sheet'",
            "expected": A1Range(sheet_name="'My Custom Sheet'"),
        },
    ]

    for tc in testcases:
        r = A1Range.from_notation(tc["notation"])
        assert r == tc["expected"]
        assert r.notation == tc["notation"]
