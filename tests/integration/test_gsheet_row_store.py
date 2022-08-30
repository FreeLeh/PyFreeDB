import pytest

from pyfreedb.row import GoogleSheetRowStore, Ordering, models

from .conftest import IntegrationTestConfig


class Customer(models.Model):
    name = models.StringField()
    age = models.IntegerField()
    dob = models.StringField(column_name="date of birth")


@pytest.mark.integration
def test_gsheet_row_store_integration(config: IntegrationTestConfig) -> GoogleSheetRowStore:
    row_store = GoogleSheetRowStore(
        config.auth_client,
        spreadsheet_id=config.spreadsheet_id,
        sheet_name="row_store",
        object_cls=Customer,
    )
    # Sheet is empty, expects empty list.
    result = row_store.select("name", "age").execute()
    assert result == []

    assert 0 == row_store.count().execute()

    # Insert some data, expects no exception raised.
    rows = [
        Customer(name="name1", age=10, dob="1-1-1999"),
        Customer(name="name2", age=11, dob="1-1-2000"),
        Customer(name="name3", age=12, dob="1-1-2001"),
    ]
    row_store.insert(rows).execute()

    # Sheet no longer empty, expects it returns 3 rows.
    returned_rows = row_store.select("name", "age", "dob").execute()
    assert returned_rows == rows

    # More complex select (multiple args)?
    rows = row_store.select("name", "age").where("age < ? AND age > ?", 12, 10).execute()
    assert rows == [Customer(name="name2", age=11)]

    # Update one of the row, expects only 1 rows that changed.
    rows_changed = row_store.update({"name": "name4"}).where("age = ?", 10).execute()
    assert rows_changed == 1

    # If no where clause, update all.
    rows_changed = row_store.update({"dob": "1-1-2002"}).execute()
    assert rows_changed == 3

    # It should reflect the previous update and return in descending order by age.
    rows = row_store.select("name").order_by(Ordering.DESC("age")).execute()
    assert rows == [Customer(name="name3"), Customer(name="name2"), Customer(name="name4")]

    # Delete with where clause.
    rows_deleted = row_store.delete().where("name = ?", "name2").execute()
    assert rows_deleted == 1

    rows = row_store.select("name").execute()
    assert rows == [Customer(name="name4"), Customer(name="name3")]

    # Count should works.
    assert 2 == row_store.count().execute()

    # Delete all rows.
    rows_deleted = row_store.delete().execute()
    assert rows_deleted == 2

    rows = row_store.select("name").execute()
    assert rows == []
