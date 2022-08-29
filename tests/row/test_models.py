import pytest

from pyfreedb.row import models


class A(models.Model):
    integer_field = models.IntegerField()
    float_field = models.FloatField()
    string_field = models.StringField()
    bool_field = models.BoolField()


class B(A):
    another_field = models.StringField()


def test_model_mro() -> None:
    obj = A()
    a_fields = list(obj._fields.keys())
    assert a_fields == ["integer_field", "float_field", "string_field", "bool_field"]

    # Parent class' field should come first.
    obj = B()
    b_fields = list(obj._fields.keys())
    assert b_fields == a_fields + ["another_field"]


def test_model() -> None:
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


def test_model_type_check() -> None:
    # Should be able to handle None.
    obj = A()
    obj.bool_field = None
    obj.bool_field = models.NotSet

    # Should raise TypeError when we pass wrong type.
    try:
        obj.bool_field = "hello"
        pytest.fail("should raise TypeError")
    except TypeError:
        pass

    try:
        A(bool_field="hello")
        pytest.fail("should raise TypeError")
    except TypeError:
        pass
