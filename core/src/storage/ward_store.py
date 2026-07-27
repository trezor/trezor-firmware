from micropython import const

from storage import common

_NAMESPACE = common.APP_AUTHDB

# Persistent (flash) storage keys.
_COUNTERS = const(0x00)  # per-wallet durable counter_loc table
_QUEUE = const(0x05)  # WARD pending candidates (multi-slot, keyed by pending_id)
_PENDING_SEQ = const(0x06)  # monotonic pending_id allocator (device-global, never reused)

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
# WARD pending-intent queue (key _QUEUE, PERSISTENT). MULTI-SLOT + PULL MODEL:
# several intents may be in flight at once, each addressed by a device-global
# pending_id (allocated monotonically, never reused). The queue value is a
# concatenation of length-framed records:
#   [body_len:2][ body ]  repeated
# where each body is:
#   [pending_id:4][wallet_id:20][counter_T:4][state:1][root_T:32][mac_T:32]
#   [addr_len:2][address][ov_len:2][old_value][nv_len:2][new_value]
# At WARDQueueUpdate the intent is stored PENDING with the counter_T the device
# derived and PLACEHOLDER root/mac (not yet computed). At WARDPerformUpdate the
# device pulls a proof, computes (root_T, mac_T), and marks it COMMITTED via
# queue_set_computed(); only then are root/mac meaningful (root_T == EMPTY_ROOT
# then marks a candidate that empties the tree, mac_T all-zero). A per-wallet cap
# of MAX_PENDING bounds the on-device storage.
# ---------------------------------------------------------------------------

QUEUE_PENDING = const(0x00)
QUEUE_COMMITTED = const(0x01)
MAX_PENDING = const(8)  # per-wallet cap on simultaneously queued intents

_ZERO_MAC = b"\x00" * 32

# Body field offsets (fixed prefix before the variable-length tail).
_OFF_PID = const(0)
_OFF_WID = const(4)
_OFF_CTR = const(24)
_OFF_STATE = const(28)
_OFF_ROOT = const(29)
_OFF_MAC = const(61)
_OFF_TAIL = const(93)  # start of [addr_len][addr][ov_len][ov][nv_len][nv]


def queue_alloc_id() -> int:
    """Allocate a fresh, device-global pending_id. Monotonic and never reused, so
    a stale WARDPerformUpdate can never alias a different queued intent."""
    raw = common.get(_NAMESPACE, _PENDING_SEQ)
    cur = int.from_bytes(raw, "big") if raw else 0
    nxt = cur + 1
    common.set(_NAMESPACE, _PENDING_SEQ, nxt.to_bytes(4, "big"))
    return nxt


def _load_records() -> list[bytes]:
    raw = common.get(_NAMESPACE, _QUEUE, public=True)
    records = []  # type: list[bytes]
    if not raw:
        return records
    off = 0
    n = len(raw)
    while off + 2 <= n:
        body_len = int.from_bytes(raw[off : off + 2], "big")
        off += 2
        records.append(bytes(raw[off : off + body_len]))
        off += body_len
    return records


def _save_records(records: list[bytes]) -> None:
    if not records:
        common.delete(_NAMESPACE, _QUEUE, public=True)
        return
    out = bytearray()
    for body in records:
        out += len(body).to_bytes(2, "big")
        out += body
    common.set(_NAMESPACE, _QUEUE, bytes(out), public=True)


def _rec_pid(body: bytes) -> int:
    return int.from_bytes(body[_OFF_PID : _OFF_PID + 4], "big")


def _rec_wid(body: bytes) -> bytes:
    return bytes(body[_OFF_WID : _OFF_WID + WALLET_ID_LENGTH])


def _read_lv(body: bytes, off: int) -> tuple[bytes, int]:
    """Read a 2-byte length-prefixed field at off; return (value, next_off)."""
    ln = int.from_bytes(body[off : off + 2], "big")
    off += 2
    return bytes(body[off : off + ln]), off + ln


def _rec_address(body: bytes) -> bytes:
    address, _ = _read_lv(body, _OFF_TAIL)
    return address


def _parse_body(
    body: bytes,
) -> tuple[int, int, bytes, bytes, bytes, bytes | None, bytes | None]:
    """Return (counter, state, address, old_value, new_value, root, mac).
    root/mac are None until the intent is COMMITTED, and also None (empty tree)
    when a COMMITTED candidate stored EMPTY_ROOT."""
    counter = int.from_bytes(body[_OFF_CTR : _OFF_CTR + 4], "big")
    state = body[_OFF_STATE]
    root = bytes(body[_OFF_ROOT : _OFF_ROOT + ROOT_LENGTH])
    mac = bytes(body[_OFF_MAC : _OFF_MAC + 32])
    address, off = _read_lv(body, _OFF_TAIL)
    old_value, off = _read_lv(body, off)
    new_value, off = _read_lv(body, off)
    if state != QUEUE_COMMITTED or root == EMPTY_ROOT:
        return counter, state, address, old_value, new_value, None, None
    return counter, state, address, old_value, new_value, root, mac


def _build_body(
    pending_id: int,
    wallet_id: bytes,
    counter: int,
    state: int,
    root: bytes,
    mac: bytes,
    address: bytes,
    old_value: bytes,
    new_value: bytes,
) -> bytes:
    return (
        pending_id.to_bytes(4, "big")
        + wallet_id
        + counter.to_bytes(4, "big")
        + bytes([state])
        + root
        + mac
        + len(address).to_bytes(2, "big")
        + address
        + len(old_value).to_bytes(2, "big")
        + old_value
        + len(new_value).to_bytes(2, "big")
        + new_value
    )


def queue_put(
    wallet_id: bytes,
    pending_id: int,
    counter: int,
    address: bytes,
    old_value: bytes,
    new_value: bytes,
) -> None:
    """Store an approved edit INTENT as PENDING under pending_id (pull model:
    no proof, no root/mac yet -- those are filled by queue_set_computed at
    WARDPerformUpdate). Replaces any record with the same pending_id; otherwise
    appends. Raises ValueError if the wallet already holds MAX_PENDING intents.
    """
    records = _load_records()

    # Per-wallet cap (a same-pending_id replacement does not count against it).
    count = 0
    for body in records:
        if _rec_wid(body) == wallet_id and _rec_pid(body) != pending_id:
            count += 1
    if count >= MAX_PENDING:
        raise ValueError("pending queue is full for this wallet")

    body = _build_body(
        pending_id,
        wallet_id,
        counter,
        QUEUE_PENDING,
        EMPTY_ROOT,
        _ZERO_MAC,
        address,
        old_value,
        new_value,
    )

    for i in range(len(records)):
        if _rec_pid(records[i]) == pending_id:
            records[i] = body
            break
    else:
        records.append(body)
    _save_records(records)


def queue_set_computed(
    wallet_id: bytes,
    pending_id: int,
    root: bytes | None,
    mac: bytes | None,
) -> None:
    """Fill the computed (root_T, mac_T) for a queued intent and mark it COMMITTED
    (WARDPerformUpdate). root/mac None means the candidate empties the tree."""
    stored_root = root if root is not None else EMPTY_ROOT
    stored_mac = mac if mac is not None else _ZERO_MAC
    if len(stored_root) != ROOT_LENGTH or len(stored_mac) != 32:
        raise ValueError("root and mac must be 32 bytes")

    records = _load_records()
    for i in range(len(records)):
        body = records[i]
        if _rec_pid(body) == pending_id and _rec_wid(body) == wallet_id:
            counter, _state, address, old_value, new_value, _r, _m = _parse_body(body)
            records[i] = _build_body(
                pending_id,
                wallet_id,
                counter,
                QUEUE_COMMITTED,
                stored_root,
                stored_mac,
                address,
                old_value,
                new_value,
            )
            _save_records(records)
            return
    raise ValueError("No pending candidate for pending_id")


def queue_get(
    wallet_id: bytes,
    pending_id: int,
) -> tuple[int, int, bytes, bytes, bytes, bytes | None, bytes | None] | None:
    """Return (counter, state, address, old_value, new_value, root, mac) for
    (wallet_id, pending_id), or None. root/mac are None until COMMITTED (and for a
    COMMITTED candidate that empties the tree)."""
    for body in _load_records():
        if _rec_pid(body) == pending_id and _rec_wid(body) == wallet_id:
            return _parse_body(body)
    return None


def queue_list(wallet_id: bytes) -> list[tuple[int, bytes]]:
    """Return (pending_id, address) for every intent queued for wallet_id,
    in insertion (allocation) order."""
    out = []  # type: list[tuple[int, bytes]]
    for body in _load_records():
        if _rec_wid(body) == wallet_id:
            out.append((_rec_pid(body), _rec_address(body)))
    return out


def queue_count(wallet_id: bytes) -> int:
    """Number of intents currently queued for wallet_id."""
    n = 0
    for body in _load_records():
        if _rec_wid(body) == wallet_id:
            n += 1
    return n


def queue_drop(wallet_id: bytes, pending_id: int) -> bool:
    """Delete the (wallet_id, pending_id) candidate. Returns True if one was
    removed, False if no such candidate existed."""
    records = _load_records()
    kept = [
        b
        for b in records
        if not (_rec_pid(b) == pending_id and _rec_wid(b) == wallet_id)
    ]
    if len(kept) != len(records):
        _save_records(kept)
        return True
    return False


def queue_drop_all(wallet_id: bytes) -> int:
    """Delete every candidate queued for wallet_id. Returns the count removed.
    Wallet-scoped: candidates for other (hidden) wallets are left intact."""
    records = _load_records()
    kept = [b for b in records if _rec_wid(b) != wallet_id]
    dropped = len(records) - len(kept)
    if dropped:
        _save_records(kept)
    return dropped
