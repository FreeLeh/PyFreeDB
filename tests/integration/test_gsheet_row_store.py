from ast import Mod
import pytest

from pyfreedb.row import GoogleSheetRowStore, Ordering, models

from .conftest import IntegrationTestConfig


class Customer(models.Model):
    name = models.StringField()
    age = models.IntegerField()
    dob = models.StringField(column_name="date of birth")


@pytest.mark.integration
def test_gsheet_row_store_integration(config: IntegrationTestConfig) -> None:
    return
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
        Customer(name="name1", age=10, dob="1999-01-01"),
        Customer(name="name2", age=11, dob="2000-01-01"),
        Customer(name="name3", age=12, dob="2001-01-01"),
    ]
    row_store.insert(rows).execute()

    # Sheet no longer empty, expects it returns 3 rows.
    returned_rows = row_store.select("name", "age", "dob").execute()
    assert returned_rows == rows

    # More complex select (multiple args)?
    rows = row_store.select("name", "age").where("age < ? AND age > ?", 12, 10).execute()
    assert rows == [Customer(name="name2", age=11)]

    rows = row_store.select().where("dob = ?", "1999-01-01").execute()
    assert rows == [Customer(name="name1", age=10, dob="1999-01-01")]

    # Update one of the row, expects only 1 rows that changed.
    rows_changed = row_store.update({"name": "name4"}).where("age = ?", 10).execute()
    assert rows_changed == 1

    # If no where clause, update all.
    rows_changed = row_store.update({"dob": "2002-01-01"}).execute()
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

    assert False


class Model(models.Model):
    integer_field = models.IntegerField()
    float_field = models.FloatField()

@pytest.mark.integration
def test_gsheet_row_edge_cases(config: IntegrationTestConfig) -> None:
    row_store = GoogleSheetRowStore(
        config.auth_client,
        spreadsheet_id=config.spreadsheet_id,
        sheet_name="row_store_edge_cases",
        object_cls=Model,
    )

    inserted_rows = [
        Model(integer_field=1, float_field=1.0),
        Model(integer_field=9007199254740992, float_field=1.7976931348623157),
        Model(integer_field=9007199254740993, float_field=1.797693134862315999),
    ]

    expected_rows = [
        Model(integer_field=1, float_field=1.0),
        Model(integer_field=9007199254740992, float_field=1.7976931348623157),

        # truncated to fit 64-bit floating point.
        Model(integer_field=9007199254740992, float_field=1.797693134862316),
    ]
    row_store.insert(inserted_rows).execute()

    returned_rows = row_store.select().execute()
    assert expected_rows == returned_rows
