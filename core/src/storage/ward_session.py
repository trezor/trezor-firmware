from micropython import const

from storage import cache
from storage.cache_common import APP_WARD_ROOT_RECORD, APP_WARD_SYNC_RECORD
from storage.ward_store import ROOT_LENGTH, WALLET_ID_LENGTH

SYNC_NONCE = const(0x00)
SYNC_ATTESTED = const(0x01)
NONCE_LENGTH = const(32)
_ZERO_MAC = b"\x00" * 32
EMPTY_ROOT = b"\x00" * ROOT_LENGTH


def sync_begin(wallet_id: bytes, nonce: bytes) -> None:
    """Start a sync round in volatile per-power-cycle storage."""
    if len(nonce) != NONCE_LENGTH:
        raise ValueError("nonce must be 32 bytes")
    record = wallet_id + nonce + bytes([SYNC_NONCE]) + b"\x00" * 4 + _ZERO_MAC
    cache.get_sessionless_cache().set(APP_WARD_SYNC_RECORD, record)


def sync_set_attested(wallet_id: bytes, counter: int, mac: bytes | None) -> None:
    """Record the accepted WM attestation (counter_ext, mac_ext) for this round."""
    raw = cache.get_sessionless_cache().get(APP_WARD_SYNC_RECORD)
    if not raw or bytes(raw[0:WALLET_ID_LENGTH]) != wallet_id:
        raise ValueError("no sync round for wallet_id")
    stored_mac = mac if mac is not None else _ZERO_MAC
    if len(stored_mac) != 32:
        raise ValueError("mac must be 32 bytes")
    buf = bytearray(raw)
    off = WALLET_ID_LENGTH + NONCE_LENGTH
    buf[off] = SYNC_ATTESTED
    buf[off + 1 : off + 5] = counter.to_bytes(4, "big")
    buf[off + 5 : off + 37] = stored_mac
    cache.get_sessionless_cache().set(APP_WARD_SYNC_RECORD, bytes(buf))


def sync_get(wallet_id: bytes) -> tuple[bytes, int, int, bytes | None] | None:
    """Return (nonce, state, counter_ext, mac_ext) for the active volatile round."""
    raw = cache.get_sessionless_cache().get(APP_WARD_SYNC_RECORD)
    if not raw or bytes(raw[0:WALLET_ID_LENGTH]) != wallet_id:
        return None
    off = WALLET_ID_LENGTH
    nonce = bytes(raw[off : off + NONCE_LENGTH])
    off += NONCE_LENGTH
    state = raw[off]
    counter = int.from_bytes(raw[off + 1 : off + 5], "big")
    mac = bytes(raw[off + 5 : off + 37])
    return nonce, state, counter, (None if mac == _ZERO_MAC else mac)


def sync_clear() -> None:
    """Clear the volatile sync-round context."""
    cache.get_sessionless_cache().delete(APP_WARD_SYNC_RECORD)


def root_set(wallet_id: bytes, root: bytes | None) -> None:
    """Install the authenticated root for the active power cycle."""
    stored_root = root if root is not None else EMPTY_ROOT
    if len(stored_root) != ROOT_LENGTH:
        raise ValueError("root must be 32 bytes")
    cache.get_sessionless_cache().set(APP_WARD_ROOT_RECORD, wallet_id + stored_root)


def root_get(wallet_id: bytes) -> tuple[bool, bytes | None]:
    """Return (present, root) for the active power-cycle authenticated root."""
    raw = cache.get_sessionless_cache().get(APP_WARD_ROOT_RECORD)
    if not raw or bytes(raw[0:WALLET_ID_LENGTH]) != wallet_id:
        return False, None
    root = bytes(raw[WALLET_ID_LENGTH : WALLET_ID_LENGTH + ROOT_LENGTH])
    return True, (None if root == EMPTY_ROOT else root)


def root_clear() -> None:
    """Clear the volatile authenticated root."""
    cache.get_sessionless_cache().delete(APP_WARD_ROOT_RECORD)
