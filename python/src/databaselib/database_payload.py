from typing import Any

from .library import dumps, hexlify, sha256
from .time import Time


class DatabasePayload:
    def __init__(
        self,
        identifier: bytes,
        revision_number: int,
        global_time: Time,
        digest: bytes,
    ):
        self.identifier = identifier
        self.revision_number = revision_number
        self.global_time = global_time
        self.digest = digest

    def to_json(self) -> Any:
        return {
            "identifier": hexlify(self.identifier).decode(),
            "revision_number": self.revision_number,
            "global_time": self.global_time.to_json(),
            "digest": hexlify(self.digest).decode(),
        }

    def to_bytes(self) -> bytes:
        return dumps(self.to_json()).encode()

    def to_digest(self) -> bytes:
        return sha256(self.to_bytes()).digest()
