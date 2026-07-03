from micropython import const

from storage import common

_NAMESPACE = common.APP_AUTHDB

_ROOTS              = const(0x00)  # flat table of wallet records
_CACHE              = const(0x01)  # offline cache: variable-length per-address metadata
_DEVICE_ID_OVERRIDE = const(0x02)  # debug only: injected device_id
_QUEUE              = const(0x03)  # offline operation queue: wallet-scoped, append-only
_SYNC               = const(0x04)  # per-wallet offline-sync counters

WALLET_ID_LENGTH = const(32)
ROOT_LENGTH      = const(32)
MAX_WALLETS      = const(16)
# Record layout: [root: 32][wallet_id: 32][counter: 4]
#
# NOTE: this table can hold one root per wallet_id (up to MAX_WALLETS), but
# host-facing root sync (e.g. a future AuthDbGetOfflineOperations-style
# upload) must only ever read/sync the root for the CURRENTLY ACTIVE
# wallet_id -- never enumerate or sync roots across every wallet_id stored
# on this physical device.
_RECORD_SIZE     = const(68)

MAX_CACHE_ENTRIES = const(64)
# Cache record layout (variable length):
#   [addr_len: 1B][address: addr_len B]
#   [label_len: 1B][label: label_len B]   (0 = absent)
#   [data_mac_present: 1B][data_mac: 32B] (0x01 = present, 0x00 = absent)

MAX_OFFLINE_QUEUE_ENTRIES = const(64)  # per wallet
# Queue record layout (variable length), FIFO by append order:
#   [wallet_id: 32]
#   [mac: 32]
#   [sequence: 4]
#   [addr_len: 4][address: addr_len B]
#   [old_len: 4][old_value: old_len B]   (0 = address absent / INSERT)
#   [new_len: 4][new_value: new_len B]   (0 = delete)
#
# Kept in its own namespace, separate from `_ROOTS`, and scoped by wallet_id
# from the start -- unlike `_CACHE`, which has no wallet_id column at all
# and therefore leaks entries across wallets sharing one device.

MAX_SYNC_WALLETS = const(16)
# Sync record layout: [wallet_id: 32][next_sequence: 4][last_applied_sequence: 4]
# Kept separate from `_ROOTS` on purpose: `clear_root()` deletes the entire
# wallet row (including its counter) whenever the tree becomes empty via a
# DELETE, which would otherwise silently reset offline-sync bookkeeping too.
_SYNC_RECORD_SIZE = const(40)


def _load_table() -> bytearray:
    raw = common.get(_NAMESPACE, _ROOTS, public=True)
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
    """Look up the root for wallet_id.

    NOTE: callers doing host-facing sync must only ever call this for the
    currently active wallet_id -- never iterate this table across wallets.
    """
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off < 0:
        return None
    return bytes(table[off : off + ROOT_LENGTH])


def set_root(wallet_id: bytes, root: bytes) -> None:
    if len(root) != ROOT_LENGTH:
        raise ValueError("Root must be 32 bytes")
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off >= 0:
        table[off : off + ROOT_LENGTH] = root
    else:
        if len(table) // _RECORD_SIZE >= MAX_WALLETS:
            raise ValueError("Too many wallets")
        table += root + wallet_id + b"\x00\x00\x00\x00"
    _save_table(table)


def clear_root(wallet_id: bytes) -> None:
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off < 0:
        return
    table[off : off + _RECORD_SIZE] = b""
    _save_table(table)


def get_counter(wallet_id: bytes) -> int:
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off < 0:
        return 0
    ctr_off = off + ROOT_LENGTH + WALLET_ID_LENGTH
    return int.from_bytes(table[ctr_off : ctr_off + 4], "big")


def increment_counter(wallet_id: bytes) -> int:
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off < 0:
        raise ValueError("No record for wallet_id")
    ctr_off = off + ROOT_LENGTH + WALLET_ID_LENGTH
    new_val = int.from_bytes(table[ctr_off : ctr_off + 4], "big") + 1
    table[ctr_off : ctr_off + 4] = new_val.to_bytes(4, "big")
    _save_table(table)
    return new_val


# ---------------------------------------------------------------------------
# Offline cache — per-address label + data_mac storage
# ---------------------------------------------------------------------------

def _load_cache() -> bytearray:
    raw = common.get(_NAMESPACE, _CACHE, public=True)
    return bytearray(raw) if raw else bytearray()


def _save_cache(cache: bytearray) -> None:
    common.set(_NAMESPACE, _CACHE, bytes(cache), public=True)


def _iter_cache(cache: bytearray):
    """Yield (start_offset, address, label_bytes, data_mac_or_None) for each record."""
    off = 0
    while off < len(cache):
        start = off
        addr_len = cache[off]; off += 1
        address = bytes(cache[off : off + addr_len]); off += addr_len
        label_len = cache[off]; off += 1
        label_bytes = bytes(cache[off : off + label_len]); off += label_len
        present = cache[off]; off += 1
        if present:
            data_mac = bytes(cache[off : off + 32]); off += 32
        else:
            data_mac = None
        yield start, address, label_bytes, data_mac


def get_cache_entry(address: bytes) -> tuple:
    """Return (label: str|None, data_mac: bytes|None), or (None, None) if not found."""
    cache = _load_cache()
    for _start, addr, label_bytes, data_mac in _iter_cache(cache):
        if addr == address:
            label = label_bytes.decode() if label_bytes else None
            return label, data_mac
    return None, None


def set_cache_entry(address: bytes, label, data_mac) -> None:
    """Upsert a cache entry. Raises ValueError if cache is full on a new insert."""
    label_bytes = label.encode() if label else b""
    if len(address) > 255 or len(label_bytes) > 255:
        raise ValueError("address or label too long")
    cache = _load_cache()
    # Find and remove existing entry if present
    count = 0
    found_start = -1
    found_end = -1
    for start, addr, _lb, _dm in _iter_cache(cache):
        count += 1
        if addr == address:
            found_start = start
            # Compute end of this record
            off = start + 1 + len(addr) + 1 + len(_lb) + 1
            if _dm is not None:
                off += 32
            found_end = off
    if found_start >= 0:
        cache[found_start:found_end] = b""
        count -= 1
    if count >= MAX_CACHE_ENTRIES:
        raise ValueError("Cache full")
    # Build new record
    rec = bytearray()
    rec.append(len(address))
    rec += address
    rec.append(len(label_bytes))
    rec += label_bytes
    if data_mac is not None:
        rec.append(1)
        rec += data_mac
    else:
        rec.append(0)
    cache += rec
    _save_cache(cache)


def delete_cache_entry(address: bytes) -> None:
    """Remove the cache entry for address; no-op if absent."""
    cache = _load_cache()
    for start, addr, _lb, _dm in _iter_cache(cache):
        if addr == address:
            off = start + 1 + len(addr) + 1 + len(_lb) + 1
            if _dm is not None:
                off += 32
            cache[start:off] = b""
            _save_cache(cache)
            return


def wipe_cache() -> None:
    """Delete the entire offline cache."""
    common.set(_NAMESPACE, _CACHE, b"", public=True)


def get_all_cache_entries() -> list:
    """Return list of (address: bytes, label: str|None, data_mac: bytes|None)."""
    cache = _load_cache()
    result = []
    for _start, addr, label_bytes, data_mac in _iter_cache(cache):
        label = label_bytes.decode() if label_bytes else None
        result.append((addr, label, data_mac))
    return result


# ---------------------------------------------------------------------------
# Debug: device_id override
# ---------------------------------------------------------------------------

def get_device_id_override() -> bytes | None:
    return common.get(_NAMESPACE, _DEVICE_ID_OVERRIDE, public=True)


def set_device_id_override(device_id: bytes) -> None:
    common.set(_NAMESPACE, _DEVICE_ID_OVERRIDE, device_id, public=True)


# ---------------------------------------------------------------------------
# Offline-sync counters (next_sequence / last_applied_sequence) per wallet
# ---------------------------------------------------------------------------

def _load_sync() -> bytearray:
    raw = common.get(_NAMESPACE, _SYNC, public=True)
    return bytearray(raw) if raw else bytearray()


def _save_sync(table: bytearray) -> None:
    common.set(_NAMESPACE, _SYNC, bytes(table), public=True)


def _find_sync_record(table: bytearray, wallet_id: bytes) -> int:
    for off in range(0, len(table), _SYNC_RECORD_SIZE):
        if table[off : off + WALLET_ID_LENGTH] == wallet_id:
            return off
    return -1


def _ensure_sync_record(table: bytearray, wallet_id: bytes) -> int:
    """Return the offset of wallet_id's sync record, creating it (next_sequence=1) if absent."""
    off = _find_sync_record(table, wallet_id)
    if off >= 0:
        return off
    if len(table) // _SYNC_RECORD_SIZE >= MAX_SYNC_WALLETS:
        raise ValueError("Too many wallets")
    off = len(table)
    table += wallet_id + (1).to_bytes(4, "big") + (0).to_bytes(4, "big")
    return off


def get_next_sequence(wallet_id: bytes) -> int:
    """Peek at the sequence number that would be assigned to the next queued operation."""
    table = _load_sync()
    off = _find_sync_record(table, wallet_id)
    if off < 0:
        return 1
    seq_off = off + WALLET_ID_LENGTH
    return int.from_bytes(table[seq_off : seq_off + 4], "big")


def take_next_sequence(wallet_id: bytes) -> int:
    """Atomically assign and persist the next sequence number for wallet_id."""
    table = _load_sync()
    off = _ensure_sync_record(table, wallet_id)
    seq_off = off + WALLET_ID_LENGTH
    sequence = int.from_bytes(table[seq_off : seq_off + 4], "big")
    table[seq_off : seq_off + 4] = (sequence + 1).to_bytes(4, "big")
    _save_sync(table)
    return sequence


def get_last_applied_sequence(wallet_id: bytes) -> int:
    table = _load_sync()
    off = _find_sync_record(table, wallet_id)
    if off < 0:
        return 0
    seq_off = off + WALLET_ID_LENGTH + 4
    return int.from_bytes(table[seq_off : seq_off + 4], "big")


def set_last_applied_sequence(wallet_id: bytes, sequence: int) -> None:
    """Persist the highest sequence this device has itself verified and applied.

    This is the ONLY value AuthDbDeleteOfflineOperations trusts for garbage
    collection -- it is never taken from a host-supplied argument.
    """
    table = _load_sync()
    off = _ensure_sync_record(table, wallet_id)
    seq_off = off + WALLET_ID_LENGTH + 4
    table[seq_off : seq_off + 4] = sequence.to_bytes(4, "big")
    _save_sync(table)


# ---------------------------------------------------------------------------
# Offline operation queue -- wallet-scoped, append-only, bounded, FIFO
# ---------------------------------------------------------------------------

def _load_queue() -> bytearray:
    raw = common.get(_NAMESPACE, _QUEUE, public=True)
    return bytearray(raw) if raw else bytearray()


def _save_queue(queue: bytearray) -> None:
    common.set(_NAMESPACE, _QUEUE, bytes(queue), public=True)


def _iter_queue(queue: bytearray):
    """Yield (start, end, wallet_id, sequence, address, old_value, new_value, mac)."""
    off = 0
    while off < len(queue):
        start = off
        wallet_id = bytes(queue[off : off + WALLET_ID_LENGTH]); off += WALLET_ID_LENGTH
        mac = bytes(queue[off : off + 32]); off += 32
        sequence = int.from_bytes(queue[off : off + 4], "big"); off += 4
        addr_len = int.from_bytes(queue[off : off + 4], "big"); off += 4
        address = bytes(queue[off : off + addr_len]); off += addr_len
        old_len = int.from_bytes(queue[off : off + 4], "big"); off += 4
        old_value = bytes(queue[off : off + old_len]); off += old_len
        new_len = int.from_bytes(queue[off : off + 4], "big"); off += 4
        new_value = bytes(queue[off : off + new_len]); off += new_len
        yield start, off, wallet_id, sequence, address, old_value, new_value, mac


def get_offline_queue(wallet_id: bytes) -> list:
    """Return [(sequence, address, old_value, new_value, mac), ...] in FIFO order."""
    queue = _load_queue()
    return [
        (sequence, address, old_value, new_value, mac)
        for _start, _end, wid, sequence, address, old_value, new_value, mac in _iter_queue(queue)
        if wid == wallet_id
    ]


def offline_queue_count(wallet_id: bytes) -> int:
    queue = _load_queue()
    return sum(
        1
        for _start, _end, wid, _seq, _addr, _old, _new, _mac in _iter_queue(queue)
        if wid == wallet_id
    )


def append_offline_operation(
    wallet_id: bytes, sequence: int, address: bytes, old_value: bytes, new_value: bytes, mac: bytes
) -> None:
    """Append an already-sequenced offline operation to the queue.

    The caller must obtain `sequence` from `take_next_sequence()` first, so
    that sequence assignment and the queue-full check happen in the order the
    caller intends (typically: check capacity, take the sequence, append).
    Raises ValueError if wallet_id's queue is already at MAX_OFFLINE_QUEUE_ENTRIES.
    """
    # 255 is a flash-usage sanity cap, not a wire-format limit: the length
    # prefixes below are 4 bytes each, not tied to this value.
    if len(address) > 255 or len(old_value) > 255 or len(new_value) > 255:
        raise ValueError("address/old_value/new_value too long")
    if len(mac) != 32:
        raise ValueError("mac must be 32 bytes")
    if offline_queue_count(wallet_id) >= MAX_OFFLINE_QUEUE_ENTRIES:
        raise ValueError("Offline queue full")

    queue = _load_queue()
    rec = bytearray()
    rec += wallet_id
    rec += mac
    rec += sequence.to_bytes(4, "big")
    rec += len(address).to_bytes(4, "big"); rec += address
    rec += len(old_value).to_bytes(4, "big"); rec += old_value
    rec += len(new_value).to_bytes(4, "big"); rec += new_value
    queue += rec
    _save_queue(queue)


def delete_offline_operations_upto(wallet_id: bytes, max_sequence: int) -> int:
    """Delete wallet_id's queued operations with sequence <= max_sequence. Returns count deleted."""
    queue = _load_queue()
    keep = bytearray()
    deleted = 0
    for start, end, wid, sequence, _addr, _old, _new, _mac in _iter_queue(queue):
        if wid == wallet_id and sequence <= max_sequence:
            deleted += 1
        else:
            keep += queue[start:end]
    if deleted:
        _save_queue(keep)
    return deleted


def wipe_offline_queue(wallet_id: bytes) -> None:
    """Delete all of wallet_id's queued operations, regardless of sequence."""
    queue = _load_queue()
    keep = bytearray()
    for start, end, wid, _seq, _addr, _old, _new, _mac in _iter_queue(queue):
        if wid != wallet_id:
            keep += queue[start:end]
    _save_queue(keep)
