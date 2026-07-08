from micropython import const

from storage import common

_NAMESPACE = common.APP_AUTHDB

_ROOTS = const(0x00)  # flat table of wallet records
# 0x01 (_CACHE), 0x02 (_DEVICE_ID_OVERRIDE), 0x03 (_QUEUE), 0x04 (_SYNC) removed with
# the offline-cache / device-id-override / offline-queue interfaces. Do not reuse.

WALLET_ID_LENGTH = const(32)
ROOT_LENGTH = const(32)
MAX_WALLETS = const(16)
# Record layout: [root: 32][wallet_id: 32][counter: 4][reserved: 4]
#
# NOTE: holds one root per wallet_id (up to MAX_WALLETS). Callers must only ever
# read the root for the CURRENTLY ACTIVE wallet_id -- never enumerate across wallets.
#
# The trailing 4 bytes are reserved (formerly last_applied_sequence, used by the removed
# offline-sync path); kept so the record size is unchanged. A wallet_id, once used, keeps
# its slot permanently.
_RECORD_SIZE = const(72)

# Sentinel meaning "no root" for a wallet_id that DOES have a storage record (its counter
# is already in use). A real Merkle root being all-zero is cryptographically meaningless
# (SHA-256 output), so this sentinel can't collide with genuine data.
EMPTY_ROOT = b"\x00" * 32


def _load_table() -> bytearray:
    raw = common.get(_NAMESPACE, _ROOTS, public=True)
    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "storage: opened _ROOTS table (%d bytes, %d wallet record(s))",
            len(raw) if raw else 0,
            (len(raw) // _RECORD_SIZE) if raw else 0,
        )
    return bytearray(raw) if raw else bytearray()


def _save_table(table: bytearray) -> None:
    common.set(_NAMESPACE, _ROOTS, bytes(table), public=True)


def _find_record(table: bytearray, wallet_id: bytes) -> int:
    """Return byte offset of the record matching wallet_id, or -1."""
    for off in range(0, len(table), _RECORD_SIZE):
        if table[off + ROOT_LENGTH : off + ROOT_LENGTH + WALLET_ID_LENGTH] == wallet_id:
            return off
    return -1


def get_root(wallet_id: bytes) -> bytes | None:
    """Look up the root for wallet_id. None if absent OR cleared (EMPTY_ROOT)."""
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off < 0:
        if __debug__:
            from trezor import log
            from ubinascii import hexlify

            log.debug(
                __name__,
                "storage: get_root(wallet_id=%s) -> no record (empty tree)",
                hexlify(wallet_id).decode(),
            )
        return None
    root = bytes(table[off : off + ROOT_LENGTH])
    result = None if root == EMPTY_ROOT else root
    if __debug__:
        from trezor import log
        from ubinascii import hexlify

        log.debug(
            __name__,
            "storage: get_root(wallet_id=%s) -> %s",
            hexlify(wallet_id).decode(),
            hexlify(result).decode() if result else "EMPTY (cleared)",
        )
    return result


def get_counter(wallet_id: bytes) -> int:
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off < 0:
        return 0
    ctr_off = off + ROOT_LENGTH + WALLET_ID_LENGTH
    return int.from_bytes(table[ctr_off : ctr_off + 4], "big")


def commit_root_and_counter(wallet_id: bytes, new_root: bytes | None) -> int:
    """Atomically persist root (or EMPTY_ROOT) and an incremented counter in a single
    storage write -- used by update_leaf.py and set_root.py's debug-bypass path.
    Returns the new counter value.
    """
    if new_root is not None and len(new_root) != ROOT_LENGTH:
        raise ValueError("Root must be 32 bytes")
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off < 0:
        if new_root is None:
            raise ValueError("No record for wallet_id")
        if len(table) // _RECORD_SIZE >= MAX_WALLETS:
            raise ValueError("Too many wallets")
        new_counter = 1
        table += new_root + wallet_id + new_counter.to_bytes(4, "big") + b"\x00\x00\x00\x00"
        _save_table(table)
        return new_counter

    ctr_off = off + ROOT_LENGTH + WALLET_ID_LENGTH
    new_counter = int.from_bytes(table[ctr_off : ctr_off + 4], "big") + 1
    table[off : off + ROOT_LENGTH] = new_root if new_root is not None else EMPTY_ROOT
    table[ctr_off : ctr_off + 4] = new_counter.to_bytes(4, "big")
    _save_table(table)
    return new_counter


def commit_root_and_counter_value(wallet_id: bytes, new_root: bytes | None, counter: int) -> None:
    """Like commit_root_and_counter(), but jumps straight to `counter` instead of
    incrementing -- used by set_root.py's verified-mac path, which installs a
    caller-attested (root, counter) pair.
    """
    if new_root is not None and len(new_root) != ROOT_LENGTH:
        raise ValueError("Root must be 32 bytes")
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off < 0:
        if new_root is None:
            raise ValueError("No record for wallet_id")
        if len(table) // _RECORD_SIZE >= MAX_WALLETS:
            raise ValueError("Too many wallets")
        table += new_root + wallet_id + counter.to_bytes(4, "big") + b"\x00\x00\x00\x00"
        _save_table(table)
        return
    ctr_off = off + ROOT_LENGTH + WALLET_ID_LENGTH
    table[off : off + ROOT_LENGTH] = new_root if new_root is not None else EMPTY_ROOT
    table[ctr_off : ctr_off + 4] = counter.to_bytes(4, "big")
    _save_table(table)
