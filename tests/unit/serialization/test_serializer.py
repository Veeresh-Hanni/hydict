from datetime import datetime

import pytest

from hydict.serialization import Serializer


def test_serialize_string():
    serializer = Serializer()

    value = "Veeresh"

    encoded = serializer.serialize(value)

    assert encoded == '"Veeresh"'


def test_deserialize_string():
    serializer = Serializer()

    value = serializer.deserialize('"Veeresh"')

    assert value == "Veeresh"

def test_serialize_dict():
    serializer = Serializer()

    value = {
        "name": "Veeresh",
        "age": 20,
        "skills": ["Python", "Django"],
    }

    encoded = serializer.serialize(value)

    assert isinstance(encoded, str)

    decoded = serializer.deserialize(encoded)

    assert decoded == value


def test_serialize_datetime_as_isoformat():
    serializer = Serializer()
    value = {"created_at": datetime(2026, 11, 5, 20, 45, 0)}

    encoded = serializer.serialize(value)

    assert serializer.deserialize(encoded) == {
        "created_at": "2026-11-05T20:45:00"
    }


def test_serialize_unsupported_object_raises_type_error():
    serializer = Serializer()

    with pytest.raises(TypeError):
        serializer.serialize(object())


def test_serialize_basic_types():
    serializer = Serializer()

    values = [
        "Veeresh",
        20,
        3.14,
        True,
        False,
        None,
        [1, 2, 3],
        {"name": "Veeresh"},
    ]

    for value in values:
        encoded = serializer.serialize(value)
        decoded = serializer.deserialize(encoded)

        assert decoded == value