from re import L
from .conftest import Config

from pyfreeleh.providers.google.auth.service_account import ServiceAccountGoogleAuthClient
from pyfreeleh.row.gsheet import GoogleSheetRowStore, Ordering


def gsheet_row_store_integration(config: Config) -> GoogleSheetRowStore:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    auth_client = ServiceAccountGoogleAuthClient.from_service_account_info(config.service_account_info, scopes=scopes)

    row_store = GoogleSheetRowStore(
        auth_client,
        spreadsheet_id=config.spreadsheet_id,
        sheet_name=config.sheet_name,
        columns=["name", "age", "dob"],
    )

    # Sheet is empty, expects empty list.
    result = row_store.select("name", "age").execute()
    assert result == []

    # Insert some data, expects no exception raised.
    rows = [
        {"name": "name1", "age": 10, "dob": "1-1-1999"},
        {"name": "name2", "age": 11, "dob": "1-1-2000"},
        {"name": "name3", "age": 12, "dob": "1-1-2001"},
    ]
    row_store.insert(rows).execute()

    # Sheet no longer empty, expects it returns 3 rows.
    returned_rows = row_store.select("name", "age", "dob").execute()
    assert returned_rows == rows

    # More complex select (multiple args)?
    rows = row_store.select("name", "age").where("age < ? AND age > ?", 12, 10).execute()
    assert rows == [{"name": "name2", "age": 11}]

    # Update one of the row, expects only 1 rows that changed.
    rows_changed = row_store.update({"name": "name4"}).where("age = ?", 10).execute()
    assert rows_changed == 1

    # If no where clause, update all.
    rows_changed = row_store.update({"dob": "1-1-2002"}).execute()
    assert rows_changed == 3

    # It should reflect the previous update and return in descending order by age.
    rows = row_store.select("name").order_by(age=Ordering.DESC).execute()
    assert rows == [{"name": "name3"}, {"name": "name2"}, {"name": "name4"}]

    # Delete with where clause.
    rows_deleted = row_store.delete().where("name = ?", "name2").execute()
    assert rows_deleted == 1

    rows = row_store.select("name").execute()
    assert rows == [{"name": "name4"}, {"name": "name3"}]

    # Delete all rows.
    rows_deleted = row_store.delete().execute()
    assert rows_deleted == 2

    rows = row_store.select("name").execute()
    assert rows == []

    row_store.close()
    return row_store


def test_gsheet_row_store_integration(config: Config):
    try:
        row_store = gsheet_row_store_integration(config)
    finally:
        # _sheet_id and _scratchpad_sheet_id is not guaranteed to exists. Should not used outside test env.
        # Ideally we should not use this to do cleanup.
        row_store._wrapper.delete_sheet(config.spreadsheet_id, row_store._sheet_id)
        row_store._wrapper.delete_sheet(config.spreadsheet_id, row_store._scratchpad_sheet_id)
