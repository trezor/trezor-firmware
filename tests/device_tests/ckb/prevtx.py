"""Host-side CKB molecule tx-hash reference for the CKB device tests.

This is an independent re-implementation of the device's RawTransaction
serialization (apps.ckb.sign_tx). The device verifies an input's capacity by
recomputing the hash of its previous transaction, so the tests need to compute
that same hash on the host to build inputs whose OutPoint matches a synthetic
previous transaction.
"""

from hashlib import blake2b

from trezorlib import ckb

# Same lock script code hash the other CKB fixtures use.
LOCK_CODE_HASH = bytes.fromhex(
    "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8"
)


def _u32(value: int) -> bytes:
    return value.to_bytes(4, "little")


def _u64(value: int) -> bytes:
    return value.to_bytes(8, "little")


def _blob(data: bytes) -> bytes:
    return _u32(len(data)) + bytes(data)


def _hash(data: bytes) -> bytes:
    return blake2b(data, digest_size=32, person=b"ckb-default-hash").digest()


def _script(code_hash: bytes, hash_type: int, args: bytes) -> bytes:
    args_s = _blob(args)
    off_code = 16
    off_ht = off_code + 32
    off_args = off_ht + 1
    total = off_args + len(args_s)
    return (
        _u32(total)
        + _u32(off_code)
        + _u32(off_ht)
        + _u32(off_args)
        + bytes(code_hash)
        + bytes([hash_type])
        + args_s
    )


def _cell_output(o) -> bytes:
    lock = _script(o.lock_code_hash, o.lock_hash_type, o.lock_args)
    if o.type_code_hash:
        type_ = _script(o.type_code_hash, o.type_hash_type or 0, o.type_args or b"")
    else:
        type_ = b""
    off_cap = 16
    off_lock = off_cap + 8
    off_type = off_lock + len(lock)
    total = off_type + len(type_)
    return (
        _u32(total)
        + _u32(off_cap)
        + _u32(off_lock)
        + _u32(off_type)
        + _u64(o.capacity)
        + lock
        + type_
    )


def _cell_input(i) -> bytes:
    return (
        _u64(i.since or 0)
        + bytes(i.previous_output_tx_hash)
        + _u32(i.previous_output_index)
    )


def _cell_dep(d) -> bytes:
    return bytes(d.tx_hash) + _u32(d.index) + bytes([d.dep_type])


def _vec_fixed(items: list[bytes]) -> bytes:
    return _u32(len(items)) + b"".join(items)


def _vec_dynamic(items: list[bytes]) -> bytes:
    if not items:
        return _u32(4)
    header = 4 + len(items) * 4
    offsets = []
    cur = header
    for it in items:
        offsets.append(cur)
        cur += len(it)
    return _u32(cur) + b"".join(_u32(o) for o in offsets) + b"".join(items)


def raw_tx_hash(inputs, outputs, outputs_data, cell_deps, version=0, header_deps=None):
    header_deps = header_deps or []
    version_b = _u32(version)
    cell_deps_b = _vec_fixed([_cell_dep(d) for d in cell_deps])
    header_deps_b = _vec_fixed([bytes(h) for h in header_deps])
    inputs_b = _vec_fixed([_cell_input(i) for i in inputs])
    outputs_b = _vec_dynamic([_cell_output(o) for o in outputs])
    outputs_data_b = _vec_dynamic([_blob(d) for d in outputs_data])

    off_v = 4 + 6 * 4
    off_cd = off_v + 4
    off_hd = off_cd + len(cell_deps_b)
    off_in = off_hd + len(header_deps_b)
    off_out = off_in + len(inputs_b)
    off_od = off_out + len(outputs_b)
    total = off_od + len(outputs_data_b)

    raw = (
        _u32(total)
        + _u32(off_v)
        + _u32(off_cd)
        + _u32(off_hd)
        + _u32(off_in)
        + _u32(off_out)
        + _u32(off_od)
        + version_b
        + cell_deps_b
        + header_deps_b
        + inputs_b
        + outputs_b
        + outputs_data_b
    )
    return _hash(raw)


def message_digest(message: bytes) -> bytes:
    """blake2b_256(personal="ckb-default-hash", "Nervos Message:" || message),
    as ckb-cli and Neuron compute it."""
    h = blake2b(digest_size=32, person=b"ckb-default-hash")
    h.update(b"Nervos Message:")
    h.update(message)
    return h.digest()


def recover_lock_args(signature: bytes, digest: bytes) -> bytes:
    """Lock args (blake160 of the pubkey) recovered from a CKB signature.

    ``signature`` is the device's native [R(32) | S(32) | recovery_id(1)], and
    the recovery runs on the host with a third-party ECDSA implementation.
    """
    from ecdsa import SECP256k1, VerifyingKey
    from ecdsa.util import sigdecode_string

    if len(signature) != 65:
        raise ValueError(f"expected a 65-byte CKB signature, got {len(signature)}")
    recid = signature[64]
    candidates = VerifyingKey.from_public_key_recovery_with_digest(
        signature[:64], digest, SECP256k1, sigdecode=sigdecode_string
    )
    if recid >= len(candidates):
        raise ValueError(f"recovery id {recid} has no candidate key")
    return _hash(candidates[recid].to_string("compressed"))[:20]


def make_dao(c: int, ar: int, s: int, u: int) -> bytes:
    """Pack a header's 32-byte ``dao`` field (C, AR, S, U as uint64 LE)."""
    return _u64(c) + _u64(ar) + _u64(s) + _u64(u)


def header_hash(header) -> bytes:
    """Hash of a Molecule ``Header``; mirrors the device's _serialize_header."""
    blob = (
        _u32(header.version)
        + _u32(header.compact_target)
        + _u64(header.timestamp)
        + _u64(header.number)
        + _u64(header.epoch)
        + bytes(header.parent_hash)
        + bytes(header.transactions_root)
        + bytes(header.proposals_hash)
        + bytes(header.extra_hash)
        + bytes(header.dao)
        + bytes(header.nonce)
    )
    return _hash(blob)


def sphincs_lock_args(public_key: bytes, variant: int) -> bytes:
    """blake2b_256(personal="ckb-sphincs+-sct",
    [0x80, 0x01, 0x01, 0x01, variant << 1] || public_key).

    Catches a wrong hashing of the returned key, not a wrong key.
    """
    h = blake2b(digest_size=32, person=b"ckb-sphincs+-sct")
    h.update(bytes([0x80, 0x01, 0x01, 0x01, (variant << 1) & 0xFF]))
    h.update(public_key)
    return h.digest()


def bytes_opt(data: bytes | None) -> bytes:
    """Molecule ``BytesOpt``: length-prefixed bytes when present, nothing when
    absent."""
    return _blob(data) if data is not None else b""


def build_witness_args(lock_size, input_type=None, output_type=None) -> bytes:
    """Molecule WitnessArgs with the lock blanked to ``lock_size`` zero bytes;
    mirrors the device's _build_witness_args."""
    lock_s = _blob(bytes(lock_size))
    input_s = bytes_opt(input_type)
    output_s = bytes_opt(output_type)
    off_lock = 16
    off_input = off_lock + len(lock_s)
    off_output = off_input + len(input_s)
    total = off_output + len(output_s)
    return (
        _u32(total)
        + _u32(off_lock)
        + _u32(off_input)
        + _u32(off_output)
        + lock_s
        + input_s
        + output_s
    )


def sighash_all(tx_hash, witnesses, group_indices, inputs_count) -> bytes:
    """Compute sighash_all; mirrors the device's _compute_sighash_all."""
    h = blake2b(digest_size=32, person=b"ckb-default-hash")
    h.update(tx_hash)
    first = witnesses[group_indices[0]]
    h.update(_u64(len(first)) + first)
    for idx in group_indices[1:]:
        if idx < len(witnesses):
            h.update(_u64(len(witnesses[idx])) + witnesses[idx])
    for idx in range(inputs_count, len(witnesses)):
        h.update(_u64(len(witnesses[idx])) + witnesses[idx])
    return h.digest()


def occupied_capacity(
    lock_args_len, type_args_len, data_len, has_type_script=True
) -> int:
    """Occupied capacity in shannons; mirrors the device's _occupied_capacity.

    `has_type_script` is explicit because `type_args_len=0` alone is ambiguous:
    a DAO cell has a type script with empty args and still occupies its 33
    fixed bytes.
    """
    occupied_bytes = 8 + 32 + 1 + lock_args_len + data_len
    if has_type_script:
        occupied_bytes += 32 + 1 + type_args_len
    return occupied_bytes * 100_000_000


def dao_maximum_withdraw(capacity, occupied, ar_deposit, ar_withdraw) -> int:
    """Max withdraw (deposit + compensation); mirrors the device's
    _dao_withdraw_value (RFC 0023)."""
    counted = capacity - occupied
    return counted * ar_withdraw // ar_deposit + occupied


def synth_prev_tx(capacities: list[int], salt: int = 0):
    """Build a minimal previous tx whose outputs carry the given capacities.

    Returns (CkbPrevTx, tx_hash). Output i has capacity ``capacities[i]`` and can
    be spent by an input with ``previous_output_index = i``. ``salt`` varies the
    lock args so distinct inputs can reference distinct previous transactions
    even when they carry the same capacity.
    """
    lock_args = bytes([salt & 0xFF]) + b"\x11" * 19
    outputs = [
        ckb.create_cell_output(
            capacity=c,
            lock_code_hash=LOCK_CODE_HASH,
            lock_hash_type=1,
            lock_args=lock_args,
        )
        for c in capacities
    ]
    outputs_data = [b"" for _ in capacities]
    tx_hash = raw_tx_hash([], outputs, outputs_data, [])
    prev = ckb.create_prev_tx(outputs=outputs)
    return prev, tx_hash


def ckb_tx_message_all(
    tx_hash,
    input_cells,
    group_indices,
    first_input_type,
    first_output_type,
    witnesses_raw,
    inputs_count,
    witnesses_count,
):
    """The SPHINCS+ signing message; mirrors the device's
    _compute_ckb_tx_message_all without sharing any code with it.

    ``input_cells``: (cell output, cell data) per input; the ``*_type`` slices
    are molecule BytesOpt encodings (empty when absent).
    """
    h = blake2b(digest_size=32, person=b"ckb-sphincs+-msg")
    h.update(tx_hash)

    for cell, data in input_cells:
        h.update(_cell_output(cell))
        h.update(_u32(len(data)))
        h.update(data)

    h.update(_u32(len(first_input_type)))
    h.update(first_input_type)
    h.update(_u32(len(first_output_type)))
    h.update(first_output_type)

    for idx in group_indices[1:]:
        if idx < witnesses_count:
            raw = witnesses_raw.get(idx, b"")
            h.update(_u32(len(raw)))
            h.update(raw)

    for idx in range(inputs_count, witnesses_count):
        raw = witnesses_raw.get(idx, b"")
        h.update(_u32(len(raw)))
        h.update(raw)

    return h.digest()


def fips205_pure(message: bytes) -> bytes:
    """FIPS 205 pure signing prefix: 0x00 || len(ctx) || ctx || M, empty ctx."""
    return b"\x00\x00" + message
