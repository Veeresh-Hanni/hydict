import json
from datetime import date, datetime, time


class Serializer:

    def serialize(self, value):
        return json.dumps(value, default=self._serialize_default)

    def deserialize(self, value):
        return json.loads(value)

    @staticmethod
    def _serialize_default(value):
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()

        raise TypeError(
            f"Object of type {type(value).__name__} is not JSON serializable"
        )