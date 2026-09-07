"""Reference implementation of the unified opt-in signature hash.

Written from the message layout in doc/unified-sighash.md of Bitcoin Knots,
independently of the firmware's own implementation in
core/src/apps/bitcoin/sign_tx/sig_hasher.py, so the two can be compared. It
covers all six valid hash types, where the firmware implements only
SIGHASH_ALL | SIGHASH_UNIFIED. test_signtx_unified.py checks it against the
cross-implementation vectors before using it to verify what the device signed.
"""

from hashlib import sha256

SIGHASH_ALL = 0x01
SIGHASH_NONE = 0x02
SIGHASH_SINGLE = 0x03
SIGHASH_UNIFIED = 0x20
SIGHASH_ANYONECANPAY = 0x80

SCRIPT_TYPE_BARE = 0  # bare and P2SH
SCRIPT_TYPE_WITNESS_V0 = 1
SCRIPT_TYPE_TAPROOT = 2  # key path
SCRIPT_TYPE_TAPSCRIPT = 3


def tagged_hash(tag: str, msg: bytes) -> bytes:
    tag_digest = sha256(tag.encode()).digest()
    return sha256(tag_digest + tag_digest + msg).digest()


def compact_size(n: int) -> bytes:
    if n < 0xFD:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + n.to_bytes(2, "little")
    if n <= 0xFFFF_FFFF:
        return b"\xfe" + n.to_bytes(4, "little")
    return b"\xff" + n.to_bytes(8, "little")


def _prefixed(script: bytes) -> bytes:
    return compact_size(len(script)) + script


def _outpoint(txid_le: bytes, vout: int) -> bytes:
    return txid_le + vout.to_bytes(4, "little")


def _spent_output(amount: int, script_pubkey: bytes) -> bytes:
    return amount.to_bytes(8, "little") + _prefixed(script_pubkey)


def unified_sighash(
    version: int,
    lock_time: int,
    vin: list,
    vout: list,
    spent_outputs: list,
    in_idx: int,
    script_type: int,
    hash_type: int,
    script_code: bytes = None,
    annex: bytes = None,
    tapleaf_hash: bytes = None,
    codeseparator_pos: int = None,
) -> bytes:
    """vin is [(txid_le, vout, sequence)], vout and spent_outputs are
    [(amount, script_pubkey)]. script_code is the unprefixed scriptCode, which
    script types BARE and WITNESS_V0 require."""
    if not hash_type & SIGHASH_UNIFIED:
        raise ValueError("SIGHASH_UNIFIED is not set")
    if len(spent_outputs) != len(vin):
        raise ValueError("All spent outputs are required")
    anyonecanpay = bool(hash_type & SIGHASH_ANYONECANPAY)
    sh = hash_type & 0x1F

    m = b""
    m += b"\x00"  # epoch
    m += bytes([hash_type])
    m += version.to_bytes(4, "little")
    m += lock_time.to_bytes(4, "little") + b"\x00"  # five bytes, not four

    if not anyonecanpay:
        m += sha256(b"".join(_outpoint(t, n) for t, n, _ in vin)).digest()
        m += sha256(
            b"".join(a.to_bytes(8, "little") for a, _ in spent_outputs)
        ).digest()
        m += sha256(b"".join(_prefixed(s) for _, s in spent_outputs)).digest()
        m += sha256(b"".join(s.to_bytes(4, "little") for _, _, s in vin)).digest()

    if sh not in (SIGHASH_NONE, SIGHASH_SINGLE):
        m += sha256(b"".join(_spent_output(a, s) for a, s in vout)).digest()

    m += bytes([script_type])

    if anyonecanpay:
        txid_le, n, sequence = vin[in_idx]
        m += _outpoint(txid_le, n)
        m += _spent_output(*spent_outputs[in_idx])
        m += sequence.to_bytes(4, "little")
    else:
        m += in_idx.to_bytes(4, "little")

    if script_type in (SCRIPT_TYPE_BARE, SCRIPT_TYPE_WITNESS_V0):
        if script_code is None:
            raise ValueError("script_code is required for this script type")
        m += _prefixed(script_code)
    else:
        m += b"\x01" if annex is not None else b"\x00"
        if annex is not None:
            m += sha256(_prefixed(annex)).digest()

    if sh == SIGHASH_SINGLE:
        if in_idx >= len(vout):
            raise ValueError("SIGHASH_SINGLE with no matching output")
        m += sha256(_spent_output(*vout[in_idx])).digest()

    if script_type == SCRIPT_TYPE_TAPSCRIPT:
        if tapleaf_hash is None:
            raise ValueError("tapleaf_hash is required for tapscript")
        m += tapleaf_hash
        m += b"\x00"  # key version
        m += (
            b"\xff\xff\xff\xff"
            if codeseparator_pos is None
            else codeseparator_pos.to_bytes(4, "little")
        )

    return tagged_hash("UnifiedSighash", m)


def parse_tx(raw: bytes):
    """Deserialize a non-witness transaction into (version, vin, vout, lock_time)."""
    o = 0

    def take(n):
        nonlocal o
        o += n
        return raw[o - n : o]

    def cs():
        nonlocal o
        first = raw[o]
        o += 1
        if first < 0xFD:
            return first
        width = {0xFD: 2, 0xFE: 4, 0xFF: 8}[first]
        return int.from_bytes(take(width), "little")

    version = int.from_bytes(take(4), "little")
    vin = []
    for _ in range(cs()):
        txid_le = take(32)
        n = int.from_bytes(take(4), "little")
        take(cs())  # scriptSig
        vin.append((txid_le, n, int.from_bytes(take(4), "little")))
    vout = []
    for _ in range(cs()):
        amount = int.from_bytes(take(8), "little")
        vout.append((amount, take(cs())))
    lock_time = int.from_bytes(take(4), "little")
    assert o == len(raw)
    return version, vin, vout, lock_time
