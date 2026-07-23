from micropython import const

from storage import common

_NAMESPACE = common.APP_AUTHDB

_ROOTS = const(0x00)  # LRU cache of wallet records (see below)
# 0x01 (_CACHE), 0x02 (_DEVICE_ID_OVERRIDE), 0x03 (old _QUEUE), 0x04 (_SYNC) removed
# with the offline-cache / device-id-override / offline-queue interfaces. Do not reuse.
_QUEUE = const(0x05)  # WARD pending candidate (single active-wallet edit; MVP depth 1)
_SYNC = const(0x06)  # WARD sync-round context (per-round nonce + attested checkpoint)

WALLET_ID_LENGTH = const(20)  # BIP32 Hash160 identifier: RIPEMD160(SHA256(master pubkey))
ROOT_LENGTH = const(32)
MAX_WALLETS = const(16)  # LRU capacity
# Record layout: [root: 32][wallet_id: 20][counter: 4][qm_last_counter: 4]
#
# The table is an LRU CACHE keyed by the 20-byte wallet_id: it holds up to
# MAX_WALLETS wallets' (root, counter, qm_last_counter). Records are ordered
# least-recently-written (front) to most-recently-written (back); a write moves
# its wallet to the back, and inserting a new wallet at capacity evicts the front
# (least-recently-used) record. Callers must only ever read the record for the
# CURRENTLY ACTIVE wallet_id -- never enumerate across wallets.
#
# The trailing 4 bytes hold qm_last_counter: the Quota-Manager-attested anti-rollback
# ceiling written by AuthDbInit.
_RECORD_SIZE = const(60)

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


def get_qm_counter(wallet_id: bytes) -> int:
    """Return the stored Quota-Manager counter (anti-rollback ceiling) for wallet_id, or 0."""
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off < 0:
        return 0
    qm_off = off + ROOT_LENGTH + WALLET_ID_LENGTH + 4
    return int.from_bytes(table[qm_off : qm_off + 4], "big")


def _read_fields(table: bytearray, off: int) -> tuple[int, int]:
    """Return (counter, qm_last_counter) of the record at byte offset off."""
    ctr_off = off + ROOT_LENGTH + WALLET_ID_LENGTH
    counter = int.from_bytes(table[ctr_off : ctr_off + 4], "big")
    qm = int.from_bytes(table[ctr_off + 4 : ctr_off + 8], "big")
    return counter, qm


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


def commit_init(
    wallet_id: bytes, qm_counter: int, new_root: bytes | None, counter: int | None
) -> None:
    """Persist AuthDbInit's verified state in a single atomic write.

    Always stores qm_counter as the wallet's qm_last_counter. When new_root is supplied,
    also installs (root, counter); when it is None, the existing root/counter are left
    untouched (a fresh wallet with no root yet gets EMPTY_ROOT / counter 0).
    """
    if new_root is not None and len(new_root) != ROOT_LENGTH:
        raise ValueError("Root must be 32 bytes")
    table = _load_table()
    off = _find_record(table, wallet_id)
    if off < 0:
        stored_root = new_root if new_root is not None else EMPTY_ROOT
        stored_counter = counter if (new_root is not None and counter is not None) else 0
    elif new_root is not None:
        stored_root = new_root
        stored_counter = counter or 0
    else:
        # keep the existing root/counter, only refresh qm_last_counter
        stored_root = bytes(table[off : off + ROOT_LENGTH])
        stored_counter, _old_qm = _read_fields(table, off)
    record = (
        stored_root + wallet_id + stored_counter.to_bytes(4, "big") + qm_counter.to_bytes(4, "big")
    )
    _put_mru(table, wallet_id, record)


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
        new_counter = 1
        qm = 0
    else:
        counter, qm = _read_fields(table, off)
        new_counter = counter + 1
    stored_root = new_root if new_root is not None else EMPTY_ROOT
    record = stored_root + wallet_id + new_counter.to_bytes(4, "big") + qm.to_bytes(4, "big")
    _put_mru(table, wallet_id, record)
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
        qm = 0
    else:
        _old_counter, qm = _read_fields(table, off)
    stored_root = new_root if new_root is not None else EMPTY_ROOT
    record = stored_root + wallet_id + counter.to_bytes(4, "big") + qm.to_bytes(4, "big")
    _put_mru(table, wallet_id, record)


def commit_finalize(wallet_id: bytes, new_root: bytes | None, counter: int) -> None:
    """Install a WM-attested (root, counter) AND advance qm_last_counter to `counter`
    in a single atomic write -- used by WARDConfirmCommit. Unlike
    commit_root_and_counter_value(), this also raises the QM anti-rollback ceiling,
    because a finalized candidate is exactly the state the WM has just signed.
    """
    if new_root is not None and len(new_root) != ROOT_LENGTH:
        raise ValueError("Root must be 32 bytes")
    stored_root = new_root if new_root is not None else EMPTY_ROOT
    table = _load_table()
    record = (
        stored_root + wallet_id + counter.to_bytes(4, "big") + counter.to_bytes(4, "big")
    )
    _put_mru(table, wallet_id, record)


# ---------------------------------------------------------------------------
# WARD pending-candidate queue (key _QUEUE). MVP depth 1: at most one PENDING or
# COMMITTED candidate is stored at a time. Record layout:
#   [counter_T:4][root_T:32][mac_T:32][state:1][addr_len:2][address]
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


# ---------------------------------------------------------------------------
# WARD sync-round context (key _SYNC). One active round per wallet. Record:
#   [wallet_id:20][nonce:32][state:1][counter_ext:4][mac_ext:32]
# state SYNC_NONCE: nonce minted (WARDInitSyncRound); SYNC_ATTESTED: (counter_ext,
# mac_ext) recorded (WARDIngestAttestation). mac_ext all-zero == empty tree.
# ---------------------------------------------------------------------------

SYNC_NONCE = const(0x00)
SYNC_ATTESTED = const(0x01)
NONCE_LENGTH = const(32)


def sync_begin(wallet_id: bytes, nonce: bytes) -> None:
    """Start a sync round: store the freshly minted nonce (overwrites any prior)."""
    if len(nonce) != NONCE_LENGTH:
        raise ValueError("nonce must be 32 bytes")
    record = (
        wallet_id + nonce + bytes([SYNC_NONCE]) + b"\x00" * 4 + _ZERO_MAC
    )
    common.set(_NAMESPACE, _SYNC, record, public=True)


def sync_set_attested(wallet_id: bytes, counter: int, mac: bytes | None) -> None:
    """Record the accepted WM attestation (counter_ext, mac_ext) for this round."""
    raw = common.get(_NAMESPACE, _SYNC, public=True)
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
    common.set(_NAMESPACE, _SYNC, bytes(buf), public=True)


def sync_get(
    wallet_id: bytes,
) -> tuple[bytes, int, int, bytes | None] | None:
    """Return the sync context for wallet_id as (nonce, state, counter_ext, mac_ext),
    or None. mac_ext is None when the attested tree is empty (all-zero sentinel)."""
    raw = common.get(_NAMESPACE, _SYNC, public=True)
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
    """Delete the sync-round context (after a successful WARDMergeState)."""
    common.delete(_NAMESPACE, _SYNC, public=True)
