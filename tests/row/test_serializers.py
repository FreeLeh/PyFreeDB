from pyfreeleh.row import models
from pyfreeleh.row.serializers import ModelGoogleSheetSerializer


class ModelA(models.Model):
    field_1 = models.StringField()


def test_serialize():
    serializer = ModelGoogleSheetSerializer(ModelA)

    # Do not serialize fields that are not set.
    obj = ModelA()
    assert serializer.serialize(obj) == {}

    obj = ModelA(rid=1)
    assert serializer.serialize(obj) == {"A": 1}


def test_deserialize():
    serializer = ModelGoogleSheetSerializer(ModelA)

    obj = serializer.deserialize({"A": 1})
    assert obj.rid == 1
    assert obj.field_1 is models.NotSet
