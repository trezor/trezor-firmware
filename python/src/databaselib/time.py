from typing import Any, Dict, Set

from .library import dumps, hexlify, loads, unhexlify


class Time:
    def __init__(self, values: Dict[bytes, int]):
        self.local_times = values

    @classmethod
    def zero(cls) -> "Time":
        return cls({})

    @classmethod
    def merge_keys(
        cls, first: Dict[bytes, int], second: Dict[bytes, int]
    ) -> Set[bytes]:
        return set(first.keys()) | set(second.keys())

    def get_local_time(self, identifier: bytes) -> int:
        return self.local_times.get(identifier, 0)

    def is_immediate_successor(self, other: "Time") -> bool:
        merged_identifiers = self.merge_keys(self.local_times, other.local_times)

        different_identifiers = [
            identifier
            for identifier in merged_identifiers
            if self.get_local_time(identifier) != other.get_local_time(identifier)
        ]
        print(self.local_times)
        print(other.local_times)
        print(different_identifiers)

        if len(different_identifiers) != 1:
            return False

        different_identifier = different_identifiers[0]

        return self.get_local_time(different_identifier) + 1 == other.get_local_time(
            different_identifier
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Time):
            return False

        return all(
            [
                self.get_local_time(identifier) == other.get_local_time(identifier)
                for identifier in self.merge_keys(self.local_times, other.local_times)
            ]
        )

    def __lt__(self, other: "Time") -> bool:
        if self == other:
            return False
        return all(
            [
                self.get_local_time(identifier) <= other.get_local_time(identifier)
                for identifier in self.merge_keys(self.local_times, other.local_times)
            ]
        )

    def increment(self, identifier: bytes):
        self.local_times[identifier] = self.get_local_time(identifier) + 1

    def to_json(self):
        return {
            hexlify(identifier).decode(): value
            for identifier, value in sorted(
                self.local_times.items(), key=lambda x: x[0]
            )
        }

    def clone(self) -> "Time":
        return Time(self.local_times.copy())

    @classmethod
    def from_json(cls, json: Any) -> "Time":
        return Time(
            {unhexlify(identifier): value for identifier, value in json.items()}
        )

    def to_bytes(self) -> bytes:
        return dumps(self.to_json()).encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> "Time":
        return cls.from_json(loads(data.decode()))
