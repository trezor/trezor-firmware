from micropython import const

from storage import common

_NAMESPACE = common.APP_AUTHDB

# Persistent (flash) storage keys.
_COUNTERS = const(0x00)  # per-wallet durable counter_loc table
_QUEUE = const(0x05)  # WARD pending candidate (single active-wallet edit; MVP depth 1)

WALLET_ID_LENGTH = const(20)  # BIP32 Hash160 identifier: RIPEMD160(SHA256(master pubkey))
ROOT_LENGTH = const(32)
MAX_WALLETS = const(16)  # LRU capacity
# Record layout: [wallet_id: 20][counter: 4]
#
# The table is an LRU CACHE keyed by the 20-byte wallet_id: it holds up to
# MAX_WALLETS wallets' durable counter_loc. Records are ordered
# least-recently-written (front) to most-recently-written (back); a write moves
# its wallet to the back, and inserting a new wallet at capacity evicts the front
# (least-recently-used) record. Callers must only ever read the record for the
# CURRENTLY ACTIVE wallet_id -- never enumerate across wallets.
_RECORD_SIZE = const(24)
EMPTY_ROOT = b"\x00" * ROOT_LENGTH

def _load_table() -> bytearray:
    raw = common.get(_NAMESPACE, _COUNTERS)
    table = bytearray(raw) if raw is not None else bytearray()
    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "storage: opened _COUNTERS table (%d bytes, %d wallet record(s))",
            len(table),
            len(table) // _RECORD_SIZE,
        )
    return table


def _save_table(table: bytearray) -> None:
    if table:
        common.set(_NAMESPACE, _COUNTERS, bytes(table))
    else:
        common.delete(_NAMESPACE, _COUNTERS)


def _find_record(table: bytearray, wallet_id: bytes) -> int:
    """Return byte offset of the record matching wallet_id, or -1."""
    for off in range(0, len(table), _RECORD_SIZE):
        if table[off : off + WALLET_ID_LENGTH] == wallet_id:
            return off
    return -1


def get_counter(wallet_id: bytes) -> int:
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off < 0:
        return 0
    ctr_off = off + WALLET_ID_LENGTH
    return int.from_bytes(table[ctr_off : ctr_off + 4], "big")


def _read_counter(table: bytearray, off: int) -> int:
    ctr_off = off + WALLET_ID_LENGTH
    return int.from_bytes(table[ctr_off : ctr_off + 4], "big")


def _put_mru(table: bytearray, wallet_id: bytes, record: bytes) -> None:
    """Upsert `record` for wallet_id as the most-recently-used entry.

    Removes any existing record for wallet_id, evicts the least-recently-used
    (front) record if the cache is at capacity, then appends `record` at the
    back. Saves the table.
    """
    off = _find_record(table, wallet_id)
    # MicroPython bytearray doesn't support slice deletion (`del table[a:b]`), so drop
    # a record by rebuilding via concatenation rather than deleting in place.
    if off >= 0:
        table = table[:off] + table[off + _RECORD_SIZE :]
    elif len(table) // _RECORD_SIZE >= MAX_WALLETS:
        # evict least-recently-used (front of the table)
        table = table[_RECORD_SIZE:]
    table += record
    _save_table(table)


def commit_counter(wallet_id: bytes, counter: int) -> None:
    """Persist only the durable local rollback floor for wallet_id."""
    table = _load_table()
    record = wallet_id + counter.to_bytes(4, "big")
    _put_mru(table, wallet_id, record)


def bump_counter(wallet_id: bytes) -> int:
    """Increment and persist counter_loc; returns the new counter."""
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off < 0:
        new_counter = 1
    else:
        new_counter = _read_counter(table, off) + 1
    record = wallet_id + new_counter.to_bytes(4, "big")
    _put_mru(table, wallet_id, record)
    return new_counter


# ---------------------------------------------------------------------------
# WARD pending-candidate queue (key _QUEUE, PERSISTENT). MVP depth 1: at most one
# PENDING or COMMITTED candidate is stored at a time. Record layout:
#   [wallet_id:20][counter_T:4][root_T:32][mac_T:32][state:1][addr_len:2][address]
# root_T == EMPTY_ROOT marks a candidate that empties the tree (mac_T then all-zero).
# ---------------------------------------------------------------------------

QUEUE_PENDING = const(0x00)
QUEUE_COMMITTED = const(0x01)

_ZERO_MAC = b"\x00" * 32


def queue_put(
    wallet_id: bytes,
    counter: int,
    root: bytes | None,
    mac: bytes | None,
    address: bytes,
) -> None:
    """Store a freshly verified candidate as PENDING (overwrites any existing one)."""
    stored_root = root if root is not None else EMPTY_ROOT
    stored_mac = mac if mac is not None else _ZERO_MAC
    if len(stored_root) != ROOT_LENGTH or len(stored_mac) != 32:
        raise ValueError("root and mac must be 32 bytes")
    record = (
        wallet_id
        + counter.to_bytes(4, "big")
        + stored_root
        + stored_mac
        + bytes([QUEUE_PENDING])
        + len(address).to_bytes(2, "big")
        + address
    )
    common.set(_NAMESPACE, _QUEUE, record, public=True)


def queue_get(
    wallet_id: bytes,
) -> tuple[int, bytes | None, bytes | None, int, bytes] | None:
    """Return the queued candidate for wallet_id as
    (counter, root, mac, state, address), or None if there is none for this wallet.

    root/mac are None when the candidate empties the tree (stored EMPTY_ROOT).
    """
    raw = common.get(_NAMESPACE, _QUEUE, public=True)
    if not raw:
        return None
    if bytes(raw[0:WALLET_ID_LENGTH]) != wallet_id:
        return None
    off = WALLET_ID_LENGTH
    counter = int.from_bytes(raw[off : off + 4], "big")
    off += 4
    root = bytes(raw[off : off + ROOT_LENGTH])
    off += ROOT_LENGTH
    mac = bytes(raw[off : off + 32])
    off += 32
    state = raw[off]
    off += 1
    addr_len = int.from_bytes(raw[off : off + 2], "big")
    off += 2
    address = bytes(raw[off : off + addr_len])
    if root == EMPTY_ROOT:
        return counter, None, None, state, address
    return counter, root, mac, state, address


def queue_set_committed(wallet_id: bytes) -> None:
    """Mark the queued candidate for wallet_id COMMITTED (emitted by WARDCommitCandidate)."""
    raw = common.get(_NAMESPACE, _QUEUE, public=True)
    if not raw or bytes(raw[0:WALLET_ID_LENGTH]) != wallet_id:
        raise ValueError("No pending candidate for wallet_id")
    buf = bytearray(raw)
    buf[WALLET_ID_LENGTH + 4 + ROOT_LENGTH + 32] = QUEUE_COMMITTED
    common.set(_NAMESPACE, _QUEUE, bytes(buf), public=True)


def queue_drop() -> None:
    """Delete the queued candidate (cleared by WARDConfirmCommit)."""
    common.delete(_NAMESPACE, _QUEUE, public=True)
