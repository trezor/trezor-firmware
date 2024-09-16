from micropython import const
from typing import Optional

from storage.common import APP_DATABASE, get, set

REVISION_NUMBER = const(0x00)
IDENTIFIER = const(0x01)


# TODO: use storage counter
def get_revision_number() -> Optional[int]:
    revision_number_bytes = get(APP_DATABASE, REVISION_NUMBER, False)
    if revision_number_bytes:
        return int.from_bytes(revision_number_bytes, "big")
    return None


def set_revision_number(revision_number: int) -> None:
    set(APP_DATABASE, REVISION_NUMBER, revision_number.to_bytes(4, "big"))


def get_identifier() -> Optional[bytes]:
    return get(APP_DATABASE, IDENTIFIER, False)


def set_identifier(identifier: bytes) -> None:
    set(APP_DATABASE, IDENTIFIER, identifier)
