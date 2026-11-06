import json
from datetime import date, datetime, time


class Serializer:

    def serialize(self, value):
        return json.dumps(value, default=self._serialize_default)

    def deserialize(self, value):
        return json.loads(value, object_hook=self._deserialize_object)

    @staticmethod
    def _serialize_default(value):
        if isinstance(value, datetime):
            return {
                "__hydict_type__": "datetime",
                "value": value.isoformat(),
            }

        if isinstance(value, date):
            return {
                "__hydict_type__": "date",
                "value": value.isoformat(),
            }

        if isinstance(value, time):
            return {
                "__hydict_type__": "time",
                "value": value.isoformat(),
            }

        raise TypeError(
            f"Object of type {type(value).__name__} is not JSON serializable"
        )

    @staticmethod
    def _deserialize_object(value):
        value_type = value.get("__hydict_type__")
        serialized_value = value.get("value")

        if value_type == "datetime" and isinstance(serialized_value, str):
            return datetime.fromisoformat(serialized_value)

        if value_type == "date" and isinstance(serialized_value, str):
            return date.fromisoformat(serialized_value)

        if value_type == "time" and isinstance(serialized_value, str):
            return time.fromisoformat(serialized_value)

        return value