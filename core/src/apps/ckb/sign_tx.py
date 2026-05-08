"""CKB transaction signing handler."""

from typing import TYPE_CHECKING

from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import blake2b
from trezor.wire import DataError

from apps.common import paths
from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERN, SLIP44_ID
from . import helpers

if TYPE_CHECKING:
    from trezor.messages import (
        CKBSignTx,
        CKBTxRequest,
        CKBCellInput,
        CKBCellOutput,
        CKBCellDep,
    )
    from apps.common.keychain import Keychain


# CKB-specific constants
SIGNATURE_PLACEHOLDER_SIZE = 65  # secp256k1 recoverable signature


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


def _serialize_bytes(data: bytes) -> bytes:
    """Serialize variable-length bytes (Molecule Bytes type).

    Bytes format: length (4 bytes LE) | data
    """
    return _serialize_uint32_le(len(data)) + data


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


def _serialize_script(code_hash: bytes, hash_type: int, args: bytes) -> bytes:
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
    return tx_hash + index + dep_type


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
) -> bytes:
    """
    Compute the raw transaction hash (without witnesses).

    RawTransaction table:
    - version: uint32
    - cell_deps: CellDepVec (FixVec)
    - header_deps: Byte32Vec (FixVec, empty)
    - inputs: CellInputVec (FixVec)
    - outputs: CellOutputVec (DynVec)
    - outputs_data: BytesVec (DynVec)
    """
    version_bytes = _serialize_uint32_le(0)

    cell_deps_bytes = _serialize_vec_fixed(
        [_serialize_cell_dep(dep) for dep in cell_deps]
    )

    header_deps_bytes = _serialize_uint32_le(0)  # empty FixVec

    inputs_bytes = _serialize_vec_fixed(
        [_serialize_cell_input(inp) for inp in inputs]
    )

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
    witness_for_group: bytes,
    other_witnesses: list[bytes],
) -> bytes:
    """
    Compute sighash_all for signing.

    The sighash_all covers:
    1. transaction hash
    2. first witness in the group (with signature placeholder)
    3. other witnesses in the same group (if any)
    """
    h = blake2b(outlen=32, personal=b"ckb-default-hash")

    h.update(tx_hash)

    witness_len = len(witness_for_group)
    h.update(_serialize_uint64_le(witness_len))
    h.update(witness_for_group)

    for witness in other_witnesses:
        h.update(_serialize_uint64_le(len(witness)))
        h.update(witness)

    return h.digest()


def _create_witness_args_with_placeholder() -> bytes:
    """
    Create WitnessArgs with 65-byte zero placeholder in lock field.

    WitnessArgs table:
    - lock: Option<Bytes> - 65-byte placeholder
    - input_type: Option<Bytes> - None
    - output_type: Option<Bytes> - None
    """
    lock_bytes = bytes(SIGNATURE_PLACEHOLDER_SIZE)
    lock_serialized = _serialize_bytes(lock_bytes)

    header_size = 4 + (3 * 4)  # 16 bytes
    offset_lock = header_size
    offset_input_type = offset_lock + len(lock_serialized)
    offset_output_type = offset_input_type  # empty
    total_size = offset_output_type

    result = bytearray()
    result.extend(_serialize_uint32_le(total_size))
    result.extend(_serialize_uint32_le(offset_lock))
    result.extend(_serialize_uint32_le(offset_input_type))
    result.extend(_serialize_uint32_le(offset_output_type))
    result.extend(lock_serialized)

    return bytes(result)


@with_slip44_keychain(PATTERN, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(msg: "CKBSignTx", keychain: "Keychain") -> "CKBTxRequest":
    """
    Sign a CKB transaction.

    Streaming protocol:
    1. Receive CKBSignTx with counts
    2. Request inputs one by one
    3. Request outputs one by one (with user confirmation)
    4. Request cell_deps
    5. Compute sighash and sign
    6. Return signature
    """
    from trezor import TR
    from trezor.enums import CKBTxRequestType
    from trezor.messages import (
        CKBTxRequest,
        CKBTxRequestDetails,
        CKBTxRequestSerialized,
        CKBTxAckInput,
        CKBTxAckOutput,
        CKBTxAckCellDep,
    )
    from trezor.wire.context import call
    from trezor.ui.layouts import confirm_output, confirm_total, show_continue_in_app

    await paths.validate_path(keychain, msg.address_n)

    if msg.network not in ("Mainnet", "Testnet"):
        raise DataError("Invalid CKB network")

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
        outputs_data.append(output.data or b"")

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

    self_send_shown = False
    for i, output in enumerate(outputs):
        if not is_change_flags[i]:
            show = True
        elif not has_external_output and not self_send_shown:
            show = True
            self_send_shown = True
        else:
            show = False

        if show:
            send_amount += output.capacity
            address = helpers.encode_address_full(
                output.lock_code_hash,
                output.lock_hash_type,
                output.lock_args,
                msg.network,
            )
            amount_str = helpers.format_amount(output.capacity)

            await confirm_output(
                address,
                amount_str,
                title=TR.send__confirm_sending,
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

    # Compute transaction hash
    tx_hash = _compute_raw_tx_hash(
        inputs=inputs,
        outputs=outputs,
        outputs_data=outputs_data,
        cell_deps=cell_deps,
    )

    # Create witness placeholder and compute sighash
    witness_placeholder = _create_witness_args_with_placeholder()

    # All inputs processed by Trezor Suite belong to the same account and share the
    # same lock script. Thus, they form a single lock script group. The CKB node's
    # sighash_all logic will iterate over all inputs in the group and hash their
    # corresponding witnesses (padding with empty witnesses if not present).
    other_witnesses = [b""] * (msg.inputs_count - 1) if msg.inputs_count > 1 else []

    sighash = _compute_sighash_all(
        tx_hash=tx_hash,
        witness_for_group=witness_placeholder,
        other_witnesses=other_witnesses,
    )

    # Confirm total
    fee = msg.fee or 0
    await confirm_total(
        total_amount=helpers.format_amount(send_amount + fee),
        fee_amount=helpers.format_amount(fee),
        title=TR.words__title_summary,
    )

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
