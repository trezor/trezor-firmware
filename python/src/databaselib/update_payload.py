from typing import Any, Optional

from .library import dumps, hexlify, sha256
from .time import Time


class UpdatePayload:
    def __init__(
        self, identifier: bytes, global_time: Time, key: str, value: Optional[str]
    ):
        self.identifier = identifier
        self.global_time = global_time
        self.key = key
        self.value = value

    def to_json(self) -> Any:
        return {
            "identifier": hexlify(self.identifier).decode(),
            "global_time": self.global_time.to_json(),
            "key": self.key,
            "value": self.value,
        }

    def to_bytes(self) -> bytes:
        return dumps(self.to_json()).encode()

    @classmethod
    def from_json(cls, data: Any) -> "UpdatePayload":
        return cls(
            bytes.fromhex(data["identifier"]),
            Time.from_json(data["global_time"]),
            data["key"],
            data["value"],
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "UpdatePayload":
        return cls.from_json(dumps(data))

    def to_digest(self) -> bytes:
        return sha256(self.to_bytes()).digest()
