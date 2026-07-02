from micropython import const

from storage import common

_NAMESPACE = common.APP_AUTHDB

_ROOTS              = const(0x00)  # flat table of identity records
_CACHE              = const(0x01)  # offline cache: variable-length per-address metadata
_DEVICE_ID_OVERRIDE = const(0x02)  # debug only: injected device_id

IDENTIFIER_LENGTH = const(32)
ROOT_LENGTH       = const(32)
MAX_IDENTITIES    = const(16)
# Record layout: [identifier: 32][root: 32][counter: 4]
_RECORD_SIZE      = const(68)

MAX_CACHE_ENTRIES = const(64)
# Cache record layout (variable length):
#   [addr_len: 1B][address: addr_len B]
#   [label_len: 1B][label: label_len B]   (0 = absent)
#   [data_mac_present: 1B][data_mac: 32B] (0x01 = present, 0x00 = absent)


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
        del cache[found_start:found_end]
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
            del cache[start:off]
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
