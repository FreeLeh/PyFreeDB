from typing import List, Type

from pyfreeleh.row import models


class A(models.Model):
    integer_field = models.IntegerField()
    float_field = models.FloatField()
    string_field = models.StringField()
    bool_field = models.BoolField()


class B(A):
    another_field = models.StringField()


def test_model() -> None:
    # Parent's field should come first.
    obj = B()
    b_fields = list(obj._fields.keys())
    assert b_fields == ["rid", "integer_field", "float_field", "string_field", "bool_field", "another_field"]

    # Can instantiate using __init__.
    obj = A(integer_field=1, float_field=1.0, string_field="abcd", bool_field=False)
    assert obj.integer_field == 1
    assert obj.float_field == 1.0
    assert obj.string_field == "abcd"
    assert obj.bool_field == False

    obj = A()
    # Accesing field that is not initialised will raise an exception.
    assert obj.bool_field is models.NotSet

    # But accessing field that has value = None will not raise an exception.
    obj.bool_field = None
    _ = obj.bool_field

    # Model should be comparable.
    a1 = A()
    a2 = A()
    assert a1 == a2

    a1.integer_field = 666
    assert a1 != a2

    b = B()
    assert a1 != b

    # object that is not created by store should have _rid = NotSet
    a = A()
    assert a.rid is models.NotSet

    # rid must be the first field.
    class ReorderedPK(models.Model):
        a = models.IntegerField()
        rid = models.PrimaryKeyField()

    assert get_model_fields(ReorderedPK) == ["rid", "a"]


def get_model_fields(cls: Type[models.Model]) -> List[str]:
    return list(cls._fields.keys())
