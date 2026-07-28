"""CKB SPHINCS+ transaction signing handler.

Self-contained streaming flow that mirrors the ECDSA CKBSignTx design:
input capacities and lock scripts are verified trustlessly by streaming each
previous transaction (TXPREV*), the fee is derived from those verified
capacities (never the host), and witnesses are streamed (TXWITNESS) and folded
into the signing message exactly like the on-chain verifier expects.

The signing message is ckb_tx_message_all (blake2b personal "ckb-sphincs+-msg",
matching ckb-fips205-utils::generate_ckb_tx_message_all), not the secp256k1
sighash_all. The on-chain verifier is FIPS 205 SLH-DSA while the vendored
library is Round-3 SPHINCS+, so the message is wrapped with the FIPS 205 domain
separator before signing. SPHINCS+ signatures reach ~50 KB and are streamed back
in chunks via TXSIGCHUNK.

Nervos DAO is supported exactly like the ECDSA path: header_deps are committed
in the raw tx hash, and a phase-2 withdrawing-cell input is credited its
verified maximum withdraw value (deposit + compensation, RFC 0023) after the
deposit/withdraw block headers are checked against header_deps.
"""

from typing import TYPE_CHECKING

from trezor.crypto.hashlib import blake2b
from trezor.wire import DataError

from . import helpers
from .get_sphincs_address import (
    _CODE_HASH_MAINNET,
    _CODE_HASH_TESTNET,
    _HASH_TYPE_MAINNET,
    _HASH_TYPE_TESTNET,
    _MAX_ACCOUNT_INDEX,
    _MULTISIG_HEADER,
    _VALID_VARIANTS,
    _compute_lock_args,
    _require_sphincs_mnemonic,
    _wipe,
)

# Read-only Molecule serialization and Nervos DAO verification shared with the
# ECDSA path.
from .sign_tx import (
    _MAX_CELL_DEPS,
    _MAX_INPUTS,
    _MAX_OUTPUTS,
    _MAX_PREV_CELL_DEPS,
    _MAX_PREV_INPUTS,
    _MAX_PREV_OUTPUTS,
    _MAX_WITNESSES,
    _compute_raw_tx_hash,
    _dao_withdraw_value,
    _is_dao_withdrawing_cell,
    _serialize_bytes,
    _serialize_cell_output,
    _serialize_uint32_le,
)

if TYPE_CHECKING:
    from trezor.messages import (
        CKBCellDep,
        CKBCellInput,
        CKBCellOutput,
        CKBSphincsPlusSignTx,
        CKBTxRequest,
    )

# Signature chunk size, kept well under the THP per-message buffer (~8 KB).
_SIG_CHUNK_SIZE = 4096


def _construct_witness_lock(variant: int, public_key: bytes, signature: bytes) -> bytes:
    """Build the witness lock: multisig header || param flag || public_key || signature.

    flag = (variant << 1) | 1 sets the has-signature bit (the script-args flag
    in get_sphincs_address clears it).
    """
    flag = ((variant << 1) | 1) & 0xFF
    return _MULTISIG_HEADER + bytes([flag]) + public_key + signature


async def _stream_and_verify_prev_tx(tx_hash: bytes) -> list["CKBCellOutput"]:
    """Stream a previous transaction, recompute its hash, and return its outputs.

    The OutPoint commits to the previous RawTransaction but not to the spent
    cells' capacity or lock, so the device re-serializes the whole previous tx
    and checks the hash before trusting any of it. The returned outputs feed
    both the trustless fee check and the ckb_tx_message_all input-cell hash.
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

    if meta.inputs_count > _MAX_PREV_INPUTS:
        raise DataError("Previous transaction inputs_count out of range")
    if meta.outputs_count > _MAX_PREV_OUTPUTS:
        raise DataError("Previous transaction outputs_count out of range")
    if (meta.cell_deps_count or 0) > _MAX_PREV_CELL_DEPS:
        raise DataError("Previous transaction cell_deps_count out of range")

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


def _compute_ckb_tx_message_all(
    tx_hash: bytes,
    input_cells: list[tuple[bytes, bytes]],
    group_indices: list[int],
    first_input_type: bytes,
    first_output_type: bytes,
    witnesses_raw: dict[int, bytes],
    inputs_count: int,
    witnesses_count: int,
) -> bytes:
    """Compute ckb_tx_message_all (blake2b "ckb-sphincs+-msg").

    Follows ckb-fips205-utils::generate_ckb_tx_message_all exactly:
      1. raw tx hash
      2. every input cell: molecule(CellOutput) || u32 len || cell data
      3. first group witness: u32 len || input_type slice || u32 len || output_type slice
      4. remaining group witnesses (by index, if present): u32 len || raw witness
      5. trailing witnesses (index >= inputs_count): u32 len || raw witness
    `input_cells` holds (molecule_cell_output, cell_data) for each input in
    order; the *_type slices are the molecule BytesOpt encodings (empty for None).
    """
    h = blake2b(outlen=32, personal=b"ckb-sphincs+-msg")
    h.update(tx_hash)

    for cell_output_mol, data in input_cells:
        h.update(cell_output_mol)
        h.update(_serialize_uint32_le(len(data)))
        h.update(data)

    h.update(_serialize_uint32_le(len(first_input_type)))
    h.update(first_input_type)
    h.update(_serialize_uint32_le(len(first_output_type)))
    h.update(first_output_type)

    for idx in group_indices[1:]:
        if idx < witnesses_count:
            raw = witnesses_raw.get(idx, b"")
            h.update(_serialize_uint32_le(len(raw)))
            h.update(raw)

    for idx in range(inputs_count, witnesses_count):
        raw = witnesses_raw.get(idx, b"")
        h.update(_serialize_uint32_le(len(raw)))
        h.update(raw)

    return h.digest()


async def sign_sphincs_tx(msg: "CKBSphincsPlusSignTx") -> "CKBTxRequest":
    from trezor import TR
    from trezor.crypto import sphincsplus
    from trezor.enums import CKBTxRequestType
    from trezor.messages import (
        CKBTxAckCellDep,
        CKBTxAckInput,
        CKBTxAckOutput,
        CKBTxAckSigChunk,
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

    variant = msg.variant if msg.variant is not None else 49
    if variant not in _VALID_VARIANTS:
        raise DataError("Invalid SPHINCS+ variant")
    network = msg.network
    if network not in ("Mainnet", "Testnet"):
        raise DataError("Invalid CKB network")
    if network == "Testnet":
        await require_confirm_testnet()

    account_index = msg.account_index if msg.account_index is not None else 0
    if account_index < 0 or account_index > _MAX_ACCOUNT_INDEX:
        raise DataError("Invalid SPHINCS+ account index")

    if msg.inputs_count == 0 or msg.inputs_count > _MAX_INPUTS:
        raise DataError("Invalid inputs_count")
    if msg.outputs_count == 0 or msg.outputs_count > _MAX_OUTPUTS:
        raise DataError("Invalid outputs_count")
    cell_deps_count = msg.cell_deps_count or 0
    if cell_deps_count > _MAX_CELL_DEPS:
        raise DataError("Invalid cell_deps_count")
    if msg.witnesses_count is None:
        raise DataError("Missing witnesses_count")
    if msg.witnesses_count > _MAX_WITNESSES:
        raise DataError("Invalid witnesses_count")
    if not msg.sign_group_input_indices:
        raise DataError("Missing sign_group_input_indices")

    # Derive the signer's public key and SPHINCS+ lock script up front so we can
    # detect change outputs and locate the signing group among the inputs. The
    # seed stays in memory until the final signing step; the try/finally wipes
    # it on every exit path.
    seed = _require_sphincs_mnemonic(variant)
    try:
        public_key = sphincsplus.derive_public_key(seed, account_index, variant)
        sender_lock_args = _compute_lock_args(public_key, variant)
        if network == "Mainnet":
            sender_code_hash = _CODE_HASH_MAINNET
            sender_hash_type = _HASH_TYPE_MAINNET
        else:
            sender_code_hash = _CODE_HASH_TESTNET
            sender_hash_type = _HASH_TYPE_TESTNET

        # Stream inputs (outpoints only; capacities/locks come from the prev tx).
        inputs: list["CKBCellInput"] = []
        for i in range(msg.inputs_count):
            ack = await call(
                CKBTxRequest(
                    request_type=CKBTxRequestType.TXINPUT,
                    details=CKBTxRequestDetails(request_index=i),
                ),
                CKBTxAckInput,
            )
            if ack.input is None:
                raise DataError("Missing input data")
            if len(ack.input.previous_output_tx_hash) != 32:
                raise DataError("previous_output_tx_hash must be 32 bytes")
            inputs.append(ack.input)

        # Stream outputs and confirm the external recipients.
        outputs: list["CKBCellOutput"] = []
        outputs_data: list[bytes] = []
        is_change_flags: list[bool] = []
        has_external_output = False
        for i in range(msg.outputs_count):
            ack = await call(
                CKBTxRequest(
                    request_type=CKBTxRequestType.TXOUTPUT,
                    details=CKBTxRequestDetails(request_index=i),
                ),
                CKBTxAckOutput,
            )
            if ack.output is None:
                raise DataError("Missing output data")
            out = ack.output
            outputs.append(out)
            outputs_data.append(bytes(out.data) if out.data else b"")
            is_change = (
                out.lock_args == sender_lock_args
                and out.lock_code_hash == sender_code_hash
                and out.lock_hash_type == sender_hash_type
                and out.type_code_hash is None
                and not out.data
            )
            is_change_flags.append(is_change)
            if not is_change:
                has_external_output = True

        send_amount = 0
        total_out = 0
        for i, out in enumerate(outputs):
            total_out += out.capacity
            if is_change_flags[i] and has_external_output:
                continue
            send_amount += out.capacity
            if out.type_code_hash is not None:
                await require_confirm_type_script()
            await require_confirm_output(
                helpers.encode_address_full(
                    out.lock_code_hash, out.lock_hash_type, out.lock_args, network
                ),
                out.capacity,
                chunkify=bool(msg.chunkify),
            )

        # Stream cell deps.
        cell_deps: list["CKBCellDep"] = []
        for i in range(cell_deps_count):
            ack = await call(
                CKBTxRequest(
                    request_type=CKBTxRequestType.TXCELLDEP,
                    details=CKBTxRequestDetails(request_index=i),
                ),
                CKBTxAckCellDep,
            )
            if ack.cell_dep is None:
                raise DataError("Missing cell_dep data")
            cell_deps.append(ack.cell_dep)

        # header_deps are committed in the tx hash; the device must hash them or
        # its signature would not match the transaction the host broadcasts.
        header_deps = [bytes(h) for h in msg.header_deps] if msg.header_deps else []
        tx_hash = _compute_raw_tx_hash(
            inputs=inputs,
            outputs=outputs,
            outputs_data=outputs_data,
            cell_deps=cell_deps,
            header_deps=header_deps,
        )

        # Verify each input trustlessly by streaming its previous tx, then
        # collect the spent cell (capacity + full molecule CellOutput + data)
        # and locate the signing script group (inputs whose lock is the
        # signer's SPHINCS+ lock).
        prev_cache: dict[bytes, list["CKBCellOutput"]] = {}
        # (header index) -> (block number, accumulated rate), filled on demand
        # while verifying Nervos DAO withdrawing-cell inputs.
        header_cache: dict[int, tuple[int, int]] = {}
        input_cells: list[tuple[bytes, bytes]] = []
        group_indices: list[int] = []
        total_in = 0
        for i, inp in enumerate(inputs):
            prev_hash = bytes(inp.previous_output_tx_hash)
            prev_outputs = prev_cache.get(prev_hash)
            if prev_outputs is None:
                prev_outputs = await _stream_and_verify_prev_tx(prev_hash)
                prev_cache[prev_hash] = prev_outputs
            index = inp.previous_output_index
            if index >= len(prev_outputs):
                raise DataError("Input previous_output_index out of range")
            spent = prev_outputs[index]
            if _is_dao_withdrawing_cell(spent):
                # A DAO withdrawal unlocks deposit + compensation, so total_out
                # may validly exceed the plain input capacity. Credit the
                # verified maximum withdraw capacity instead of the raw
                # capacity.
                total_in += await _dao_withdraw_value(
                    inp, spent, header_deps, header_cache
                )
            else:
                total_in += spent.capacity
            input_cells.append(
                (
                    _serialize_cell_output(spent),
                    bytes(spent.data) if spent.data else b"",
                )
            )
            if (
                spent.lock_code_hash == sender_code_hash
                and spent.lock_hash_type == sender_hash_type
                and spent.lock_args == sender_lock_args
            ):
                group_indices.append(i)

        if not group_indices:
            raise DataError("No input belongs to the signer's SPHINCS+ lock")
        if group_indices != sorted(msg.sign_group_input_indices):
            raise DataError("sign_group_input_indices do not match the signer's inputs")

        # Stream witnesses: the first group witness carries WitnessArgs (only its
        # input_type/output_type enter the message); all others are raw bytes.
        signing_index = group_indices[0]
        if signing_index >= msg.witnesses_count:
            raise DataError("Signing witness index out of range")
        first_input_type = b""
        first_output_type = b""
        witnesses_raw: dict[int, bytes] = {}
        for i in range(msg.witnesses_count):
            ack = await call(
                CKBTxRequest(
                    request_type=CKBTxRequestType.TXWITNESS,
                    details=CKBTxRequestDetails(request_index=i),
                ),
                CKBTxAckWitness,
            )
            if i == signing_index:
                args = ack.witness_args
                if args is None:
                    raise DataError("Missing WitnessArgs for signing witness")
                # A molecule BytesOpt serializes to length-prefixed bytes when
                # present and to nothing when absent.
                first_input_type = (
                    _serialize_bytes(args.input_type)
                    if args.input_type is not None
                    else b""
                )
                first_output_type = (
                    _serialize_bytes(args.output_type)
                    if args.output_type is not None
                    else b""
                )
            else:
                if ack.witness_args is not None:
                    raise DataError("Unexpected WitnessArgs for non-signing witness")
                witnesses_raw[i] = bytes(ack.raw) if ack.raw is not None else b""

        sighash = _compute_ckb_tx_message_all(
            tx_hash=tx_hash,
            input_cells=input_cells,
            group_indices=group_indices,
            first_input_type=first_input_type,
            first_output_type=first_output_type,
            witnesses_raw=witnesses_raw,
            inputs_count=msg.inputs_count,
            witnesses_count=msg.witnesses_count,
        )

        # Fee comes from the trustlessly verified input capacities, never the host.
        if total_in < total_out:
            raise DataError("Inputs do not cover outputs")
        fee = total_in - total_out
        await require_confirm_fee_over_threshold(fee, total_out)
        await require_confirm_total(send_amount + fee, fee)

        # FIPS 205 pure signing prepends M' = 0x00 || len(ctx) || ctx || M; with
        # an empty context this is two zero bytes. The vendored Round-3 SPHINCS+
        # otherwise matches FIPS 205, so this prefix turns it into a FIPS 205
        # SLH-DSA signature.
        fips205_message = b"\x00\x00" + sighash
        signed_pk, raw_signature = sphincsplus.derive_and_sign(
            seed, account_index, variant, fips205_message
        )
    finally:
        _wipe(seed)

    if signed_pk != public_key:
        raise DataError("SPHINCS+ public key mismatch (possible fault injection)")

    full_signature = _construct_witness_lock(variant, public_key, raw_signature)

    # Stream the witness lock back in chunks (signatures exceed the THP buffer).
    total = len(full_signature)
    offset = 0
    while offset < total:
        chunk = full_signature[offset : offset + _SIG_CHUNK_SIZE]
        await call(
            CKBTxRequest(
                request_type=CKBTxRequestType.TXSIGCHUNK,
                details=CKBTxRequestDetails(
                    signature_offset=offset, signature_total_size=total
                ),
                serialized=CKBTxRequestSerialized(signature=chunk),
            ),
            CKBTxAckSigChunk,
        )
        offset += len(chunk)

    show_continue_in_app(TR.send__transaction_signed)

    return CKBTxRequest(
        request_type=CKBTxRequestType.TXFINISHED,
        serialized=CKBTxRequestSerialized(tx_hash=tx_hash),
    )
