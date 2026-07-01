from micropython import const

from storage import common

_NAMESPACE = common.APP_AUTHDB

_ROOTS = const(0x00)  # flat table of identity records

IDENTIFIER_LENGTH = const(32)
ROOT_LENGTH       = const(32)
MAX_IDENTITIES    = const(16)
# Record layout: [identifier: 32][root: 32][counter: 4]
_RECORD_SIZE      = const(68)


def _load_table() -> bytearray:
    raw = common.get(_NAMESPACE, _ROOTS, public=True)
    return bytearray(raw) if raw else bytearray()


def _save_table(table: bytearray) -> None:
    common.set(_NAMESPACE, _ROOTS, bytes(table), public=True)


def _find_record(table: bytearray, identifier: bytes) -> int:
    """Return byte offset of the record matching identifier, or -1."""
    for off in range(0, len(table), _RECORD_SIZE):
        if table[off : off + IDENTIFIER_LENGTH] == identifier:
            return off
    return -1


def get_root(identifier: bytes) -> bytes | None:
    table = _load_table()
    off = _find_record(table, identifier)
    if off < 0:
        return None
    return bytes(table[off + IDENTIFIER_LENGTH : off + IDENTIFIER_LENGTH + ROOT_LENGTH])


def set_root(identifier: bytes, root: bytes) -> None:
    if len(root) != ROOT_LENGTH:
        raise ValueError("Root must be 32 bytes")
    table = _load_table()
    off = _find_record(table, identifier)
    if off >= 0:
        table[off + IDENTIFIER_LENGTH : off + IDENTIFIER_LENGTH + ROOT_LENGTH] = root
    else:
        if len(table) // _RECORD_SIZE >= MAX_IDENTITIES:
            raise ValueError("Too many identities")
        table += identifier + root + b"\x00\x00\x00\x00"
    _save_table(table)


def clear_root(identifier: bytes) -> None:
    table = _load_table()
    off = _find_record(table, identifier)
    if off < 0:
        return
    del table[off : off + _RECORD_SIZE]
    _save_table(table)


def get_counter(identifier: bytes) -> int:
    table = _load_table()
    off = _find_record(table, identifier)
    if off < 0:
        return 0
    return int.from_bytes(
        table[off + IDENTIFIER_LENGTH + ROOT_LENGTH : off + _RECORD_SIZE], "big"
    )


def increment_counter(identifier: bytes) -> int:
    table = _load_table()
    off = _find_record(table, identifier)
    if off < 0:
        raise ValueError("No record for identifier")
    ctr_off = off + IDENTIFIER_LENGTH + ROOT_LENGTH
    new_val = int.from_bytes(table[ctr_off : ctr_off + 4], "big") + 1
    table[ctr_off : ctr_off + 4] = new_val.to_bytes(4, "big")
    _save_table(table)
    return new_val
