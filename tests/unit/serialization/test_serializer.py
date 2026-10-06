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