import typing as t
from dataclasses import dataclass

from typing_extensions import Protocol


class FirmwareIntegrityError(Exception):
    pass


class InvalidSignatureError(FirmwareIntegrityError):
    pass


class Unsigned(FirmwareIntegrityError):
    pass


class DigestCalculator(Protocol):
    def update(self, __data: bytes) -> None:
        ...

    def digest(self) -> bytes:
        ...


Hasher = t.Callable[[bytes], DigestCalculator]


@dataclass
class FirmwareHashParameters:
    hash_function: Hasher
    chunk_size: int
    padding_byte: t.Optional[bytes]
