"""CKB transaction signing handler."""

from typing import TYPE_CHECKING

from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import blake2b
from trezor.wire import DataError

from apps.common import paths
from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERN, SLIP44_ID, helpers

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import (
        CKBBlockHeader,
        CKBCellDep,
        CKBCellInput,
        CKBCellOutput,
        CKBSignTx,
        CKBTxRequest,
    )

    from apps.common.keychain import Keychain


# CKB-specific constants
SIGNATURE_PLACEHOLDER_SIZE = 65  # secp256k1 recoverable signature

# 1 byte of cell capacity is 10^8 shannons; occupied capacity is sized in bytes.
SHANNONS_PER_BYTE = 100000000

# Nervos DAO type script code hash (identical on Mainnet and Testnet). An input
# is treated as a DAO cell only if its verified previous output carries this script.
DAO_TYPE_CODE_HASH = b"\x82\xd7\x6d\x1b\x75\xfe\x2f\xd9\xa2\x7d\xfb\xaa\x65\xa0\x39\x22\x1a\x38\x0d\x76\xc9\x26\xf3\x78\xd3\xf8\x1c\xf3\xe7\xe1\x3f\x2e"
DAO_TYPE_HASH_TYPE = 1  # "type"


def _blake2b_hash(data: bytes) -> bytes:
    """Compute Blake2b hash with CKB personalization."""
    h = blake2b(data=data, outlen=32, personal=b"ckb-default-hash")
    return h.digest()


def _serialize_uint32_le(value: int) -> bytes:
    """Serialize uint32 to little-endian bytes."""
    return value.to_bytes(4, "little")


def _serialize_uint64_le(value: int) -> bytes:
    """Serialize uint64 to little-endian bytes."""
    return value.to_bytes(8, "little")


def _serialize_bytes(data: "AnyBytes") -> bytes:
    """Serialize variable-length bytes (Molecule Bytes type).

    Bytes format: length (4 bytes LE) | data
    """
    return _serialize_uint32_le(len(data)) + bytes(data)


def _serialize_cell_input(cell_input: "CKBCellInput") -> bytes:
    """
    Serialize CellInput in Molecule format.

    CellInput struct (fixed size = 44 bytes):
    - since: uint64 (8 bytes)
    - previous_output: OutPoint
        - tx_hash: byte32 (32 bytes)
        - index: uint32 (4 bytes)
    """
    since_bytes = _serialize_uint64_le(cell_input.since or 0)
    tx_hash = cell_input.previous_output_tx_hash
    if len(tx_hash) != 32:
        raise DataError("CellInput tx_hash must be 32 bytes")
    index = _serialize_uint32_le(cell_input.previous_output_index)
    return since_bytes + tx_hash + index


def _serialize_script(code_hash: "AnyBytes", hash_type: int, args: "AnyBytes") -> bytes:
    """
    Serialize Script in Molecule format (dynamic size table).

    Script table:
    - header: 4 bytes (total size) + 3 x 4 bytes (offsets)
    - code_hash: 32 bytes
    - hash_type: 1 byte
    - args: Bytes (length-prefixed)
    """
    if len(code_hash) != 32:
        raise DataError("Script code_hash must be 32 bytes")
    if hash_type not in (0, 1, 2, 4):
        raise DataError("Invalid CKB hash_type")
    hash_type_byte = bytes([hash_type])
    args_serialized = _serialize_bytes(args)

    header_size = 4 + (3 * 4)  # 16 bytes
    offset_code_hash = header_size
    offset_hash_type = offset_code_hash + 32
    offset_args = offset_hash_type + 1
    total_size = offset_args + len(args_serialized)

    result = bytearray()
    result.extend(_serialize_uint32_le(total_size))
    result.extend(_serialize_uint32_le(offset_code_hash))
    result.extend(_serialize_uint32_le(offset_hash_type))
    result.extend(_serialize_uint32_le(offset_args))
    result.extend(code_hash)
    result.extend(hash_type_byte)
    result.extend(args_serialized)

    return bytes(result)


def _serialize_cell_output(cell_output: "CKBCellOutput") -> bytes:
    """
    Serialize CellOutput in Molecule format (dynamic size table).

    CellOutput table:
    - capacity: uint64 (8 bytes)
    - lock: Script
    - type_: Option<Script>
    """
    capacity_bytes = _serialize_uint64_le(cell_output.capacity)
    lock_script = _serialize_script(
        cell_output.lock_code_hash,
        cell_output.lock_hash_type,
        cell_output.lock_args,
    )

    if cell_output.type_code_hash:
        type_script = _serialize_script(
            cell_output.type_code_hash,
            cell_output.type_hash_type or 0,
            cell_output.type_args or b"",
        )
    else:
        type_script = b""

    header_size = 4 + (3 * 4)  # 16 bytes
    offset_capacity = header_size
    offset_lock = offset_capacity + 8
    offset_type = offset_lock + len(lock_script)
    total_size = offset_type + len(type_script)

    result = bytearray()
    result.extend(_serialize_uint32_le(total_size))
    result.extend(_serialize_uint32_le(offset_capacity))
    result.extend(_serialize_uint32_le(offset_lock))
    result.extend(_serialize_uint32_le(offset_type))
    result.extend(capacity_bytes)
    result.extend(lock_script)
    result.extend(type_script)

    return bytes(result)


def _serialize_cell_dep(cell_dep: "CKBCellDep") -> bytes:
    """
    Serialize CellDep in Molecule format (fixed size = 37 bytes).

    CellDep struct:
    - out_point: OutPoint (36 bytes: tx_hash 32 + index 4)
    - dep_type: 1 byte
    """
    tx_hash = cell_dep.tx_hash
    if len(tx_hash) != 32:
        raise DataError("CellDep tx_hash must be 32 bytes")
    if cell_dep.dep_type not in (0, 1):
        raise DataError("Invalid CKB dep_type")
    index = _serialize_uint32_le(cell_dep.index)
    dep_type = bytes([cell_dep.dep_type])
    return bytes(tx_hash) + index + dep_type


def _serialize_vec_fixed(items: list[bytes]) -> bytes:
    """Serialize a vector of fixed-size items (FixVec).

    FixVec format: item_count (4 bytes LE) | items...
    """
    result = bytearray()
    result.extend(_serialize_uint32_le(len(items)))
    for item in items:
        result.extend(item)
    return bytes(result)


def _serialize_vec_dynamic(items: list[bytes]) -> bytes:
    """Serialize a vector of dynamic-size items (DynVec).

    DynVec format: total_size (4 bytes) | offset_0 | offset_1 | ... | items...
    """
    if not items:
        return _serialize_uint32_le(4)  # empty vector is just the size header

    header_size = 4 + len(items) * 4

    offsets = []
    current_offset = header_size
    for item in items:
        offsets.append(current_offset)
        current_offset += len(item)

    total_size = current_offset

    result = bytearray()
    result.extend(_serialize_uint32_le(total_size))
    for offset in offsets:
        result.extend(_serialize_uint32_le(offset))
    for item in items:
        result.extend(item)

    return bytes(result)


def _compute_raw_tx_hash(
    inputs: list["CKBCellInput"],
    outputs: list["CKBCellOutput"],
    outputs_data: list[bytes],
    cell_deps: list["CKBCellDep"],
    version: int = 0,
    header_deps: list[bytes] | None = None,
) -> bytes:
    """
    Compute the raw transaction hash (without witnesses).

    RawTransaction table:
    - version: uint32
    - cell_deps: CellDepVec (FixVec)
    - header_deps: Byte32Vec (FixVec)
    - inputs: CellInputVec (FixVec)
    - outputs: CellOutputVec (DynVec)
    - outputs_data: BytesVec (DynVec)

    ``version`` and ``header_deps`` default to the values used by transactions
    this device builds (0 and empty); they are parameterized so the same routine
    can recompute the hash of an arbitrary previous transaction for trustless
    fee verification.
    """
    version_bytes = _serialize_uint32_le(version)

    cell_deps_bytes = _serialize_vec_fixed(
        [_serialize_cell_dep(dep) for dep in cell_deps]
    )

    if header_deps:
        for header in header_deps:
            if len(header) != 32:
                raise DataError("CKB header_dep must be 32 bytes")
        header_deps_bytes = _serialize_vec_fixed([bytes(h) for h in header_deps])
    else:
        header_deps_bytes = _serialize_uint32_le(0)  # empty FixVec

    inputs_bytes = _serialize_vec_fixed([_serialize_cell_input(inp) for inp in inputs])

    outputs_bytes = _serialize_vec_dynamic(
        [_serialize_cell_output(out) for out in outputs]
    )

    outputs_data_bytes = _serialize_vec_dynamic(
        [_serialize_bytes(data) for data in outputs_data]
    )

    # Build raw transaction table (6 fields)
    header_size = 4 + (6 * 4)  # total_size + 6 field offsets

    offset_version = header_size
    offset_cell_deps = offset_version + 4
    offset_header_deps = offset_cell_deps + len(cell_deps_bytes)
    offset_inputs = offset_header_deps + len(header_deps_bytes)
    offset_outputs = offset_inputs + len(inputs_bytes)
    offset_outputs_data = offset_outputs + len(outputs_bytes)
    total_size = offset_outputs_data + len(outputs_data_bytes)

    raw_tx = bytearray()
    raw_tx.extend(_serialize_uint32_le(total_size))
    raw_tx.extend(_serialize_uint32_le(offset_version))
    raw_tx.extend(_serialize_uint32_le(offset_cell_deps))
    raw_tx.extend(_serialize_uint32_le(offset_header_deps))
    raw_tx.extend(_serialize_uint32_le(offset_inputs))
    raw_tx.extend(_serialize_uint32_le(offset_outputs))
    raw_tx.extend(_serialize_uint32_le(offset_outputs_data))
    raw_tx.extend(version_bytes)
    raw_tx.extend(cell_deps_bytes)
    raw_tx.extend(header_deps_bytes)
    raw_tx.extend(inputs_bytes)
    raw_tx.extend(outputs_bytes)
    raw_tx.extend(outputs_data_bytes)

    return _blake2b_hash(bytes(raw_tx))


def _compute_sighash_all(
    tx_hash: bytes,
    witnesses: list[bytes],
    group_indices: list[int],
    inputs_count: int,
) -> bytes:
    """
    Compute sighash_all exactly as the secp256k1_blake160 lock script does.

    The preimage hashes, in order:
    1. the raw transaction hash
    2. the first witness of the signing group (its lock field already blanked)
    3. the remaining witnesses of the same group, skipping any whose index is
       absent from the on-chain witness vector (matching the lock script's
       ITEM_MISSING break)
    4. all trailing witnesses (index >= number of inputs)
    """
    h = blake2b(outlen=32, personal=b"ckb-default-hash")
    h.update(tx_hash)

    first = witnesses[group_indices[0]]
    h.update(_serialize_uint64_le(len(first)))
    h.update(first)

    for idx in group_indices[1:]:
        if idx < len(witnesses):
            witness = witnesses[idx]
            h.update(_serialize_uint64_le(len(witness)))
            h.update(witness)

    for idx in range(inputs_count, len(witnesses)):
        witness = witnesses[idx]
        h.update(_serialize_uint64_le(len(witness)))
        h.update(witness)

    return h.digest()


def _build_witness_args(
    lock_size: int,
    input_type: "AnyBytes | None",
    output_type: "AnyBytes | None",
) -> bytes:
    """
    Build a Molecule WitnessArgs table with the lock field filled by ``lock_size``
    zero bytes (the signature placeholder hashed into the sighash_all preimage).

    WitnessArgs table (each field is a BytesOpt):
    - lock: Some(lock_size zero bytes)
    - input_type: Some(input_type) when provided, otherwise None
    - output_type: Some(output_type) when provided, otherwise None
    """
    lock_serialized = _serialize_bytes(bytes(lock_size))
    input_type_serialized = (
        _serialize_bytes(input_type) if input_type is not None else b""
    )
    output_type_serialized = (
        _serialize_bytes(output_type) if output_type is not None else b""
    )

    header_size = 4 + (3 * 4)  # 16 bytes
    offset_lock = header_size
    offset_input_type = offset_lock + len(lock_serialized)
    offset_output_type = offset_input_type + len(input_type_serialized)
    total_size = offset_output_type + len(output_type_serialized)

    result = bytearray()
    result.extend(_serialize_uint32_le(total_size))
    result.extend(_serialize_uint32_le(offset_lock))
    result.extend(_serialize_uint32_le(offset_input_type))
    result.extend(_serialize_uint32_le(offset_output_type))
    result.extend(lock_serialized)
    result.extend(input_type_serialized)
    result.extend(output_type_serialized)

    return bytes(result)


def _validate_sign_group(
    group_indices: list[int], inputs_count: int, witnesses_count: int
) -> None:
    """Validate the host-declared signing group against the transaction shape."""
    if not group_indices:
        raise DataError("Empty signing group")

    prev = -1
    for idx in group_indices:
        if idx <= prev:
            raise DataError("Signing group indices must be sorted and unique")
        if idx >= inputs_count:
            raise DataError("Signing group index out of range")
        prev = idx

    # The first group input holds the signature, so its witness must exist.
    if group_indices[0] >= witnesses_count:
        raise DataError("Signing witness index out of range")


def _serialize_header(header: "CKBBlockHeader") -> bytes:
    """
    Serialize a Molecule ``Header`` (the 192-byte fixed RawHeader struct followed
    by the 16-byte nonce). The block hash is ``blake2b`` of this serialization, so
    re-serializing on-device lets us check a host-supplied header against the
    header_dep hash the user is signing.
    """
    for field in (
        header.parent_hash,
        header.transactions_root,
        header.proposals_hash,
        header.extra_hash,
        header.dao,
    ):
        if len(field) != 32:
            raise DataError("CKB header field must be 32 bytes")
    if len(header.nonce) != 16:
        raise DataError("CKB header nonce must be 16 bytes")

    return (
        _serialize_uint32_le(header.version)
        + _serialize_uint32_le(header.compact_target)
        + _serialize_uint64_le(header.timestamp)
        + _serialize_uint64_le(header.number)
        + _serialize_uint64_le(header.epoch)
        + bytes(header.parent_hash)
        + bytes(header.transactions_root)
        + bytes(header.proposals_hash)
        + bytes(header.extra_hash)
        + bytes(header.dao)
        + bytes(header.nonce)
    )


def _is_dao_withdrawing_cell(cell: "CKBCellOutput") -> bool:
    """A Nervos DAO phase-2 withdrawing cell: the DAO type script plus 8 bytes of
    cell data holding the deposit block number (a fresh deposit cell stores 8 zero
    bytes and earns no compensation, so it is treated as a plain input)."""
    if cell.type_code_hash is None:
        return False
    if bytes(cell.type_code_hash) != DAO_TYPE_CODE_HASH:
        return False
    if (cell.type_hash_type or 0) != DAO_TYPE_HASH_TYPE:
        return False
    data = bytes(cell.data) if cell.data else b""
    return len(data) == 8 and data != bytes(8)


def _occupied_capacity(cell: "CKBCellOutput") -> int:
    """Occupied capacity in shannons: the cell's own byte size (capacity field +
    lock script + type script + data) times 10^8. Only the free capacity above
    this earns DAO compensation."""
    lock_args = bytes(cell.lock_args)
    type_args = bytes(cell.type_args) if cell.type_args else b""
    data = bytes(cell.data) if cell.data else b""
    occupied_bytes = (
        8  # capacity field
        + 32
        + 1
        + len(lock_args)  # lock script (code_hash + hash_type + args)
        + 32
        + 1
        + len(type_args)  # type script
        + len(data)
    )
    return occupied_bytes * SHANNONS_PER_BYTE


async def _verify_header(
    index: int, header_deps: list[bytes], cache: dict[int, tuple[int, int]]
) -> tuple[int, int]:
    """
    Stream the block header at ``header_deps[index]``, verify its hash, and return
    ``(block_number, accumulated_rate)``. The accumulated rate (AR) is the second
    uint64 of the 32-byte ``dao`` field. Cached per index so a header shared by
    several DAO inputs is streamed and verified once.
    """
    cached = cache.get(index)
    if cached is not None:
        return cached

    from trezor.enums import CKBTxRequestType
    from trezor.messages import CKBTxAckHeader, CKBTxRequest, CKBTxRequestDetails
    from trezor.wire.context import call

    if index >= len(header_deps):
        raise DataError("DAO header index out of range")

    ack = await call(
        CKBTxRequest(
            request_type=CKBTxRequestType.TXHEADER,
            details=CKBTxRequestDetails(request_index=index),
        ),
        CKBTxAckHeader,
    )
    if ack.header is None:
        raise DataError("Missing block header")

    if _blake2b_hash(_serialize_header(ack.header)) != header_deps[index]:
        raise DataError("CKB header hash mismatch")

    accumulated_rate = int.from_bytes(bytes(ack.header.dao)[8:16], "little")
    result = (ack.header.number, accumulated_rate)
    cache[index] = result
    return result


async def _dao_withdraw_value(
    inp: "CKBCellInput",
    spent: "CKBCellOutput",
    header_deps: list[bytes],
    header_cache: dict[int, tuple[int, int]],
) -> int:
    """
    Maximum withdraw capacity (deposit + compensation) of a Nervos DAO
    withdrawing cell, per RFC 0023:

        (capacity - occupied) * AR_withdraw / AR_deposit + occupied

    Both headers are verified against header_deps. The deposit header is pinned to
    the cell (its number must equal the deposit number stored in the cell data);
    the withdraw header is host-asserted, so the host can only shift the displayed
    fee within the signed header_deps, never the amount consensus enforces on chain.
    """
    if inp.dao_deposit_header_index is None or inp.dao_withdraw_header_index is None:
        raise DataError("DAO withdrawal input requires header indices")

    deposit_number, ar_deposit = await _verify_header(
        inp.dao_deposit_header_index, header_deps, header_cache
    )
    _, ar_withdraw = await _verify_header(
        inp.dao_withdraw_header_index, header_deps, header_cache
    )

    cell_data = spent.data
    if cell_data is None or len(cell_data) < 8:
        raise DataError("DAO withdrawing cell missing deposit block number")

    cell_deposit_number = int.from_bytes(bytes(cell_data)[:8], "little")
    if deposit_number != cell_deposit_number:
        raise DataError("DAO deposit header does not match cell")
    if ar_deposit == 0:
        raise DataError("Invalid DAO deposit rate")
    if ar_withdraw < ar_deposit:
        raise DataError("DAO compensation must be non-negative")

    occupied = _occupied_capacity(spent)
    if occupied > spent.capacity:
        raise DataError("DAO occupied capacity exceeds deposit")

    counted = spent.capacity - occupied
    return counted * ar_withdraw // ar_deposit + occupied


async def _verify_prev_tx_outputs(tx_hash: bytes) -> list["CKBCellOutput"]:
    """
    Stream a previous transaction, recompute its hash, and return its outputs.

    The CKB sighash commits to the input OutPoints but not to the capacities of
    the cells being spent, so a host could otherwise lie to the screen about the
    fee. To verify trustlessly the device re-serializes the whole previous
    RawTransaction (the only data the tx_hash commits to) with the same routine
    it uses for the current tx and checks the hash against the OutPoint. Only
    then is the spent capacity trusted. This mirrors Bitcoin legacy prevtx
    streaming.
    """
    from trezor.enums import CKBTxRequestType
    from trezor.messages import (
        CKBTxAckCellDep,
        CKBTxAckInput,
        CKBTxAckOutput,
        CKBTxAckPrevMeta,
        CKBTxRequest,
        CKBTxRequestDetails,
    )
    from trezor.wire.context import call

    meta = await call(
        CKBTxRequest(
            request_type=CKBTxRequestType.TXPREVMETA,
            details=CKBTxRequestDetails(tx_hash=tx_hash),
        ),
        CKBTxAckPrevMeta,
    )

    prev_inputs: list["CKBCellInput"] = []
    for i in range(meta.inputs_count):
        ack_in = await call(
            CKBTxRequest(
                request_type=CKBTxRequestType.TXPREVINPUT,
                details=CKBTxRequestDetails(request_index=i, tx_hash=tx_hash),
            ),
            CKBTxAckInput,
        )
        if ack_in.input is None:
            raise DataError("Missing previous transaction input")
        prev_inputs.append(ack_in.input)

    prev_outputs: list["CKBCellOutput"] = []
    prev_outputs_data: list[bytes] = []
    for i in range(meta.outputs_count):
        ack_out = await call(
            CKBTxRequest(
                request_type=CKBTxRequestType.TXPREVOUTPUT,
                details=CKBTxRequestDetails(request_index=i, tx_hash=tx_hash),
            ),
            CKBTxAckOutput,
        )
        if ack_out.output is None:
            raise DataError("Missing previous transaction output")
        prev_outputs.append(ack_out.output)
        prev_outputs_data.append(
            bytes(ack_out.output.data) if ack_out.output.data else b""
        )

    prev_cell_deps: list["CKBCellDep"] = []
    for i in range(meta.cell_deps_count or 0):
        ack_dep = await call(
            CKBTxRequest(
                request_type=CKBTxRequestType.TXPREVCELLDEP,
                details=CKBTxRequestDetails(request_index=i, tx_hash=tx_hash),
            ),
            CKBTxAckCellDep,
        )
        if ack_dep.cell_dep is None:
            raise DataError("Missing previous transaction cell_dep")
        prev_cell_deps.append(ack_dep.cell_dep)

    recomputed = _compute_raw_tx_hash(
        inputs=prev_inputs,
        outputs=prev_outputs,
        outputs_data=prev_outputs_data,
        cell_deps=prev_cell_deps,
        version=meta.version,
        header_deps=[bytes(h) for h in meta.header_deps],
    )
    if recomputed != tx_hash:
        raise DataError("Previous transaction hash mismatch")

    return prev_outputs


@with_slip44_keychain(PATTERN, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(msg: "CKBSignTx", keychain: "Keychain") -> "CKBTxRequest":
    """
    Sign a CKB transaction.

    Streaming protocol:
    1. Receive CKBSignTx with counts
    2. Request inputs one by one
    3. Request outputs one by one (with user confirmation)
    4. Request cell_deps
    5. Request witnesses (when witnesses_count is provided)
    6. Compute sighash_all and sign
    7. Return signature
    """
    from trezor import TR
    from trezor.enums import CKBTxRequestType
    from trezor.messages import (
        CKBTxAckCellDep,
        CKBTxAckInput,
        CKBTxAckOutput,
        CKBTxAckWitness,
        CKBTxRequest,
        CKBTxRequestDetails,
        CKBTxRequestSerialized,
    )
    from trezor.ui.layouts import show_continue_in_app
    from trezor.wire.context import call

    from .layout import (
        require_confirm_fee_over_threshold,
        require_confirm_output,
        require_confirm_testnet,
        require_confirm_total,
        require_confirm_type_script,
    )

    await paths.validate_path(keychain, msg.address_n)

    if msg.network not in ("Mainnet", "Testnet"):
        raise DataError("Invalid CKB network")

    if msg.network == "Testnet":
        await require_confirm_testnet()

    if msg.inputs_count == 0:
        raise DataError("Transaction must have at least one input")
    if msg.outputs_count == 0:
        raise DataError("Transaction must have at least one output")

    # Collect inputs
    inputs: list["CKBCellInput"] = []
    for i in range(msg.inputs_count):
        req = CKBTxRequest(
            request_type=CKBTxRequestType.TXINPUT,
            details=CKBTxRequestDetails(request_index=i),
        )
        ack = await call(req, CKBTxAckInput)
        if ack.input is None:
            raise DataError("Missing input data")
        inputs.append(ack.input)

    # Derive sender's lock script to detect change outputs
    node = keychain.derive(msg.address_n)
    sender_lock_args = helpers.get_lock_script_arg(node.public_key())
    sender_lock_code_hash = helpers.CODE_HASH_SECP256K1_BLAKE160
    sender_lock_hash_type = helpers.HASH_TYPE

    # Collect outputs and prepare for confirmation
    outputs: list["CKBCellOutput"] = []
    outputs_data: list[bytes] = []
    send_amount = 0
    total_out = 0
    has_external_output = False
    is_change_flags: list[bool] = []

    for i in range(msg.outputs_count):
        req = CKBTxRequest(
            request_type=CKBTxRequestType.TXOUTPUT,
            details=CKBTxRequestDetails(request_index=i),
        )
        ack = await call(req, CKBTxAckOutput)
        if ack.output is None:
            raise DataError("Missing output data")

        output = ack.output
        outputs.append(output)
        outputs_data.append(bytes(output.data) if output.data else b"")
        total_out += output.capacity

        is_change = (
            output.lock_args == sender_lock_args
            and output.lock_code_hash == sender_lock_code_hash
            and output.lock_hash_type == sender_lock_hash_type
            and output.type_code_hash is None
            and not output.data
        )
        is_change_flags.append(is_change)

        if not is_change:
            has_external_output = True

    for i, output in enumerate(outputs):
        # Hide change only when a separate external recipient is shown.
        if is_change_flags[i] and has_external_output:
            continue

        send_amount += output.capacity
        address = helpers.encode_address_full(
            output.lock_code_hash,
            output.lock_hash_type,
            output.lock_args,
            msg.network,
        )
        if output.type_code_hash is not None:
            await require_confirm_type_script()

        await require_confirm_output(
            address,
            output.capacity,
            chunkify=bool(msg.chunkify),
        )

    # Collect cell_deps
    cell_deps: list["CKBCellDep"] = []
    for i in range(msg.cell_deps_count or 0):
        req = CKBTxRequest(
            request_type=CKBTxRequestType.TXCELLDEP,
            details=CKBTxRequestDetails(request_index=i),
        )
        ack = await call(req, CKBTxAckCellDep)
        if ack.cell_dep is None:
            raise DataError("Missing cell_dep data")
        cell_deps.append(ack.cell_dep)

    # Compute transaction hash. This also validates the structural lengths of
    # inputs, outputs, and cell_deps before the (more expensive) previous-tx
    # streaming below, so malformed data fails fast.
    # header_deps are committed in the tx hash; the device must hash them or its
    # signature would not match the transaction the host broadcasts.
    header_deps = [bytes(h) for h in msg.header_deps] if msg.header_deps else []
    tx_hash = _compute_raw_tx_hash(
        inputs=inputs,
        outputs=outputs,
        outputs_data=outputs_data,
        cell_deps=cell_deps,
        header_deps=header_deps,
    )

    # Verify each input's capacity trustlessly by streaming its previous tx.
    # Cache the verified previous-tx outputs by tx_hash so a funding tx spent by
    # several inputs is streamed once.
    prev_tx_outputs: dict[bytes, list["CKBCellOutput"]] = {}
    # (header index) -> (block number, accumulated rate), filled on demand while
    # verifying Nervos DAO withdrawing-cell inputs.
    header_cache: dict[int, tuple[int, int]] = {}
    total_in = 0
    for inp in inputs:
        prev_hash = bytes(inp.previous_output_tx_hash)
        outs = prev_tx_outputs.get(prev_hash)
        if outs is None:
            outs = await _verify_prev_tx_outputs(prev_hash)
            prev_tx_outputs[prev_hash] = outs
        index = inp.previous_output_index
        if index >= len(outs):
            raise DataError("Input previous_output_index out of range")
        spent = outs[index]
        if _is_dao_withdrawing_cell(spent):
            # A DAO withdrawal unlocks deposit + compensation, so total_out may
            # validly exceed the plain input capacity. Credit the verified
            # maximum withdraw capacity instead of the raw capacity.
            total_in += await _dao_withdraw_value(inp, spent, header_deps, header_cache)
        else:
            total_in += spent.capacity

    # The host declares the witnesses and signing group; the device never guesses.
    if msg.witnesses_count is None:
        raise DataError("Missing witnesses_count")
    if not msg.sign_group_input_indices:
        raise DataError("Missing sign_group_input_indices")

    group_indices = sorted(msg.sign_group_input_indices)
    _validate_sign_group(group_indices, msg.inputs_count, msg.witnesses_count)

    signing_index = group_indices[0]
    witnesses: list[bytes] = []
    for i in range(msg.witnesses_count):
        req = CKBTxRequest(
            request_type=CKBTxRequestType.TXWITNESS,
            details=CKBTxRequestDetails(request_index=i),
        )
        ack = await call(req, CKBTxAckWitness)
        if i == signing_index:
            # Built on-device so we control the sighash bytes; only lock is blanked.
            args = ack.witness_args
            if args is None:
                raise DataError("Missing WitnessArgs for signing witness")
            lock_size = (
                args.lock_size
                if args.lock_size is not None
                else SIGNATURE_PLACEHOLDER_SIZE
            )
            if lock_size != SIGNATURE_PLACEHOLDER_SIZE:
                raise DataError("Unexpected lock size for signing witness")
            witnesses.append(
                _build_witness_args(lock_size, args.input_type, args.output_type)
            )
        else:
            if ack.witness_args is not None:
                raise DataError("Unexpected WitnessArgs for non-signing witness")
            witnesses.append(bytes(ack.raw) if ack.raw is not None else b"")

    sighash = _compute_sighash_all(
        tx_hash=tx_hash,
        witnesses=witnesses,
        group_indices=group_indices,
        inputs_count=msg.inputs_count,
    )

    # Fee comes from the trustlessly verified input capacities, never the host.
    if total_in < total_out:
        raise DataError("Inputs do not cover outputs")
    fee = total_in - total_out

    # Anchor the high-fee warning to total_out (all outputs, including change);
    # a consolidation is almost all change, so a smaller base would over-warn.
    await require_confirm_fee_over_threshold(fee, total_out)
    await require_confirm_total(send_amount + fee, fee)

    # Sign and output CKB native format: [R(32) | S(32) | recovery_id(1)]
    raw_sig = secp256k1.sign(node.private_key(), sighash, False)
    recid = raw_sig[0] - 27
    signature = raw_sig[1:65] + bytes([recid])

    show_continue_in_app(TR.send__transaction_signed)

    return CKBTxRequest(
        request_type=CKBTxRequestType.TXFINISHED,
        serialized=CKBTxRequestSerialized(
            signature=signature,
            tx_hash=tx_hash,
        ),
    )
