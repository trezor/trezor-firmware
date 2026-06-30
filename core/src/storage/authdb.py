from micropython import const

from storage import common

_NAMESPACE = common.APP_AUTHDB

_ROOT    = const(0x00)  # bytes  – 32-byte Merkle root
_COUNTER = const(0x01)  # uint32 – monotonic update counter

ROOT_LENGTH = const(32)


def get_root() -> bytes | None:
    return common.get(_NAMESPACE, _ROOT, public=True)


def set_root(root: bytes) -> None:
    if len(root) != ROOT_LENGTH:
        raise ValueError("Root must be 32 bytes")
    common.set(_NAMESPACE, _ROOT, root, public=True)


def get_counter() -> int:
    val = common.get(_NAMESPACE, _COUNTER, public=True)
    if val is None:
        return 0
    return int.from_bytes(val, "big")


def increment_counter() -> int:
    new_val = get_counter() + 1
    common.set(_NAMESPACE, _COUNTER, new_val.to_bytes(4, "big"), public=True)
    return new_val
