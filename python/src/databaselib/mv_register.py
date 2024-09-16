from typing import Any, List

from .time import Time
from .library import dumps, loads


class MVRegister:
    class SetOperation:
        def __init__(self, time: Time, value: str):
            self.value = value
            self.time = time

        def to_json(self):
            return {
                "type": "Set",
                "time": self.time.to_json(),
                "value": self.value,
            }

    def __init__(self, history: List["MVRegister.SetOperation"]):
        self.history = history
        self.compact()
        
    @classmethod
    def empty(cls):
        return cls([])

    def set(self, time: Time, value: str) -> None:
        self.history.append(MVRegister.SetOperation(time, value))
        self.compact()

    def set_resolve(self, time: Time, value: str) -> None:
        if value in self.get():
            self.history.append(MVRegister.SetOperation(time, value))
        self.compact()

    def get(self) -> List[str]:
        return [operation.value for operation in self.history]

    def compact(self):
        self.history = [
            operation
            for operation in self.history
            if not any([operation.time < other.time for other in self.history])
        ]

    def merge(self, other: "MVRegister"):
        self.history.extend(other.history)
        self.compact()

    def to_json(self) -> Any:
        return {
            "history": [operation.to_json() for operation in self.history],
        }
        
    @classmethod
    def from_json(cls, data: Any) -> "MVRegister":
        return cls([MVRegister.SetOperation(Time.from_json(operation["time"]), operation["value"]) for operation in data["history"]])
        
    def to_bytes(self) -> bytes:
        return dumps(self.to_json()).encode()
        
    @classmethod
    def from_bytes(cls, data: bytes) -> "MVRegister":
        return cls.from_json(loads(data))
