# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""CKB (Nervos Network) support for Trezor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AnyStr, NamedTuple

from . import exceptions, messages
from .tools import prepare_message_bytes, workflow

if TYPE_CHECKING:
    from .client import Session
    from .tools import Address

DEFAULT_BIP32_PATH = "m/44'/309'/0'/0/0"

# Must stay large: the device bounds how many chunks it will accept.
_SIG_CHUNK_SIZE = 4096
# Mirrors _MAX_SIGNATURE_CHUNKS in the device's verify_sphincs_message.
_MAX_SIG_CHUNKS = 256


class CkbPrevTx(NamedTuple):
    """A previous transaction streamed to the device for trustless fee checks.

    The device re-serializes these fields, recomputes the tx hash, and matches it
    against the spending input's OutPoint before trusting an output's capacity.
    """

    version: int
    inputs: list["messages.CKBCellInput"]
    outputs: list["messages.CKBCellOutput"]
    cell_deps: list["messages.CKBCellDep"]
    header_deps: list[bytes]


def _normalize_tx_hash(tx_hash: bytes | str) -> bytes:
    if isinstance(tx_hash, str):
        return bytes.fromhex(tx_hash.removeprefix("0x"))
    return bytes(tx_hash)


def create_prev_tx(
    outputs: list["messages.CKBCellOutput"],
    inputs: list["messages.CKBCellInput"] | None = None,
    cell_deps: list["messages.CKBCellDep"] | None = None,
    version: int = 0,
    header_deps: list[bytes] | None = None,
) -> CkbPrevTx:
    """Build a CkbPrevTx; outputs are mandatory, everything else defaults empty."""
    return CkbPrevTx(
        version=version,
        inputs=inputs or [],
        outputs=outputs,
        cell_deps=cell_deps or [],
        header_deps=header_deps or [],
    )


def get_address(*args: Any, **kwargs: Any) -> str:
    resp = get_authenticated_address(*args, **kwargs)
    assert resp.address is not None
    return resp.address


@workflow(capability=messages.Capability.CKB)
def get_authenticated_address(
    session: "Session",
    address_n: "Address",
    network: str,
    show_display: bool = False,
    chunkify: bool = False,
) -> messages.CKBAddress:
    return session.call(
        messages.CKBGetAddress(
            address_n=address_n,
            show_display=show_display,
            network=network,
            chunkify=chunkify,
        ),
        expect=messages.CKBAddress,
    )


@workflow(capability=messages.Capability.CKB)
def sign_message(
    session: "Session",
    address_n: "Address",
    message: AnyStr,
    network: str = "Mainnet",
    chunkify: bool = False,
) -> messages.CKBMessageSignature:
    return session.call(
        messages.CKBSignMessage(
            address_n=address_n,
            message=prepare_message_bytes(message),
            network=network,
            chunkify=chunkify,
        ),
        expect=messages.CKBMessageSignature,
    )


def verify_message(
    session: "Session",
    address: str,
    signature: bytes,
    message: AnyStr,
    network: str = "Mainnet",
    chunkify: bool = False,
) -> bool:
    try:
        session.call(
            messages.CKBVerifyMessage(
                address=address,
                signature=signature,
                message=prepare_message_bytes(message),
                network=network,
                chunkify=chunkify,
            ),
            expect=messages.Success,
        )
        return True
    except exceptions.TrezorFailure:
        return False


@workflow(capability=messages.Capability.CKB)
def sign_tx(
    session: "Session",
    address_n: "Address",
    inputs: list["messages.CKBCellInput"],
    outputs: list["messages.CKBCellOutput"],
    cell_deps: list["messages.CKBCellDep"] | None = None,
    witnesses: list["messages.CKBTxAckWitness"] | None = None,
    sign_group_input_indices: list[int] | None = None,
    network: str = "Mainnet",
    chunkify: bool = False,
    prev_txs: dict[bytes | str, CkbPrevTx] | None = None,
    header_deps: list[bytes] | None = None,
    headers: list["messages.CKBBlockHeader"] | None = None,
) -> "messages.CKBTxRequest":
    """
    Sign a CKB transaction using streaming protocol.

    Args:
        session: Trezor session instance
        address_n: BIP-32 path for signing key
        inputs: List of cell inputs to spend
        outputs: List of cell outputs to create
        cell_deps: List of cell dependencies (optional)
        witnesses: Full witness vector as CKBTxAckWitness items; the signing
            witness carries ``witness_args``, others carry ``raw``. When omitted,
            a single lock-script group is assumed (advanced txs such as Nervos
            DAO must pass an explicit vector).
        sign_group_input_indices: Inputs of the group to sign, first index holds
            the signature. Defaults to every input.
        network: "Mainnet" or "Testnet"
        chunkify: Display addresses in chunks
        prev_txs: Map of input ``previous_output_tx_hash`` to the previous
            transaction, used by the device to verify input capacities. Required
            for every distinct tx hash referenced by ``inputs``.
        header_deps: 32-byte block-header hashes committed in the tx hash. Empty
            for plain transfers; Nervos DAO withdrawals reference the deposit and
            withdraw block headers here.
        headers: Full block headers, one per ``header_deps`` entry (same order),
            served to the device on demand so it can verify Nervos DAO
            compensation. Required when any input is a DAO withdrawing cell.

    Returns:
        CKBTxRequest with signature and tx_hash when TXFINISHED
    """
    if cell_deps is None:
        cell_deps = []
    prev_tx_map = {_normalize_tx_hash(k): v for k, v in (prev_txs or {}).items()}

    if witnesses is None:
        witnesses = [create_witness_args()]
        witnesses += [create_witness_raw() for _ in range(max(0, len(inputs) - 1))]
    if sign_group_input_indices is None:
        sign_group_input_indices = list(range(len(inputs)))

    res = session.call(
        messages.CKBSignTx(
            address_n=address_n,
            network=network,
            inputs_count=len(inputs),
            outputs_count=len(outputs),
            cell_deps_count=len(cell_deps),
            witnesses_count=len(witnesses),
            sign_group_input_indices=sign_group_input_indices,
            chunkify=chunkify,
            header_deps=header_deps or [],
        ),
        expect=messages.CKBTxRequest,
    )

    res, _ = _serve_tx_requests(
        session, res, inputs, outputs, cell_deps, witnesses, prev_tx_map, headers
    )
    return res


def _sig_chunk(res: "messages.CKBTxRequest", expected_offset: int) -> tuple[bytes, int]:
    """Validate a TXSIGCHUNK request and return its payload and total size."""
    if res.serialized is None or res.serialized.signature is None:
        raise ValueError("TXSIGCHUNK request without signature data")
    if (
        res.details is None
        or res.details.signature_offset is None
        or res.details.signature_total_size is None
    ):
        raise ValueError("TXSIGCHUNK request without chunk metadata")
    if res.details.signature_offset != expected_offset:
        raise ValueError(
            f"TXSIGCHUNK out of order: offset {res.details.signature_offset}, "
            f"expected {expected_offset}"
        )
    payload = bytes(res.serialized.signature)
    if not payload:
        # Without this the offset never advances and the caller spins forever.
        raise ValueError("TXSIGCHUNK with an empty payload")
    if expected_offset + len(payload) > res.details.signature_total_size:
        raise ValueError("TXSIGCHUNK stream exceeds its declared total size")
    return payload, res.details.signature_total_size


def _serve_tx_requests(
    session: "Session",
    res: "messages.CKBTxRequest",
    inputs: list["messages.CKBCellInput"],
    outputs: list["messages.CKBCellOutput"],
    cell_deps: list["messages.CKBCellDep"],
    witnesses: list["messages.CKBTxAckWitness"],
    prev_tx_map: dict[bytes, CkbPrevTx],
    headers: list["messages.CKBBlockHeader"] | None,
) -> tuple["messages.CKBTxRequest", bytes]:
    """Serve the device's CKBTxRequest stream until TXFINISHED.

    Returns ``(final_request, signature)`` where ``signature`` concatenates any
    TXSIGCHUNK chunks the device streamed (the SPHINCS+ witness lock; empty for
    the ECDSA flow, which returns its signature in the final request instead).
    """
    from .messages import CKBTxRequestType

    def _get_prev_tx(tx_hash: bytes | None) -> CkbPrevTx:
        if tx_hash is None:
            raise ValueError("Device requested previous tx without a tx_hash")
        key = _normalize_tx_hash(tx_hash)
        if key not in prev_tx_map:
            raise ValueError(f"Missing previous tx for {key.hex()}")
        return prev_tx_map[key]

    signature = bytearray()
    sig_total: int | None = None
    while res.request_type != CKBTxRequestType.TXFINISHED:
        if res.request_type == CKBTxRequestType.TXSIGCHUNK:
            chunk, total = _sig_chunk(res, len(signature))
            if sig_total is None:
                sig_total = total
            elif total != sig_total:
                raise ValueError("TXSIGCHUNK total size changed mid-stream")
            signature.extend(chunk)
            res = session.call(
                messages.CKBTxAckSigChunk(), expect=messages.CKBTxRequest
            )
            continue

        if res.details is None:
            raise ValueError("Device response missing request details")
        details = res.details

        if res.request_type == CKBTxRequestType.TXPREVMETA:
            prev = _get_prev_tx(details.tx_hash)
            res = session.call(
                messages.CKBTxAckPrevMeta(
                    version=prev.version,
                    inputs_count=len(prev.inputs),
                    outputs_count=len(prev.outputs),
                    cell_deps_count=len(prev.cell_deps),
                    header_deps=prev.header_deps,
                ),
                expect=messages.CKBTxRequest,
            )
            continue

        idx = details.request_index
        if idx is None:
            raise ValueError("Device response missing request_index")

        if res.request_type == CKBTxRequestType.TXINPUT:
            res = session.call(
                messages.CKBTxAckInput(input=inputs[idx]),
                expect=messages.CKBTxRequest,
            )
        elif res.request_type == CKBTxRequestType.TXOUTPUT:
            res = session.call(
                messages.CKBTxAckOutput(output=outputs[idx]),
                expect=messages.CKBTxRequest,
            )
        elif res.request_type == CKBTxRequestType.TXCELLDEP:
            res = session.call(
                messages.CKBTxAckCellDep(cell_dep=cell_deps[idx]),
                expect=messages.CKBTxRequest,
            )
        elif res.request_type == CKBTxRequestType.TXWITNESS:
            res = session.call(witnesses[idx], expect=messages.CKBTxRequest)
        elif res.request_type == CKBTxRequestType.TXPREVINPUT:
            prev = _get_prev_tx(details.tx_hash)
            res = session.call(
                messages.CKBTxAckInput(input=prev.inputs[idx]),
                expect=messages.CKBTxRequest,
            )
        elif res.request_type == CKBTxRequestType.TXPREVOUTPUT:
            prev = _get_prev_tx(details.tx_hash)
            res = session.call(
                messages.CKBTxAckOutput(output=prev.outputs[idx]),
                expect=messages.CKBTxRequest,
            )
        elif res.request_type == CKBTxRequestType.TXPREVCELLDEP:
            prev = _get_prev_tx(details.tx_hash)
            res = session.call(
                messages.CKBTxAckCellDep(cell_dep=prev.cell_deps[idx]),
                expect=messages.CKBTxRequest,
            )
        elif res.request_type == CKBTxRequestType.TXHEADER:
            if headers is None or idx >= len(headers):
                raise ValueError(f"Missing block header for header_deps[{idx}]")
            res = session.call(
                messages.CKBTxAckHeader(header=headers[idx]),
                expect=messages.CKBTxRequest,
            )
        else:
            raise ValueError(f"Unknown request type: {res.request_type}")

    if sig_total is not None and len(signature) != sig_total:
        raise ValueError(
            f"Incomplete signature stream: {len(signature)} of {sig_total} bytes"
        )
    return res, bytes(signature)


class SphincsSignedTx(NamedTuple):
    """Result of a SPHINCS+ signing flow.

    ``witness_lock`` is the complete witness lock field
    ([0x80,0x00,0x01,0x01,flag] || public_key || signature) assembled from the
    TXSIGCHUNK stream; place it in the signing witness before broadcasting.
    """

    tx_hash: bytes
    witness_lock: bytes


@workflow(capability=messages.Capability.CKB)
def get_sphincs_address(
    session: "Session",
    network: str,
    account_index: int = 0,
    variant: int = 49,
    show_display: bool = False,
    chunkify: bool = False,
) -> messages.CKBSphincsPlusAddress:
    """Get the CKB SPHINCS+ post-quantum address (with lock_args and public key).

    Requires the device to be initialized with an extended BIP-39 mnemonic
    (36/54/72 words) matching the variant's security level.
    """
    return session.call(
        messages.CKBSphincsPlusGetAddress(
            account_index=account_index,
            variant=variant,
            network=network,
            show_display=show_display,
            chunkify=chunkify,
        ),
        expect=messages.CKBSphincsPlusAddress,
    )


class SphincsMessageSignature(NamedTuple):
    """Result of a SPHINCS+ message-signing flow.

    The signature itself arrives through the TXSIGCHUNK stream rather than in
    the terminal message, so it is reassembled here.
    """

    address: str
    public_key: bytes
    variant: int
    signature: bytes


@workflow(capability=messages.Capability.CKB)
def sign_sphincs_message(
    session: "Session",
    message: AnyStr,
    network: str = "Mainnet",
    account_index: int = 0,
    variant: int = 49,
    chunkify: bool = False,
) -> SphincsMessageSignature:
    """Sign a message with a CKB SPHINCS+ post-quantum key.

    SLH-DSA signatures reach ~50 kB and exceed the wire buffer, so the device
    streams them back in CKBTxRequest{TXSIGCHUNK} chunks terminated by a
    CKBSphincsPlusMessageSignature.
    """
    res = session.call(
        messages.CKBSphincsPlusSignMessage(
            account_index=account_index,
            variant=variant,
            message=prepare_message_bytes(message),
            network=network,
            chunkify=chunkify,
        )
    )

    signature = bytearray()
    sig_total: int | None = None
    while isinstance(res, messages.CKBTxRequest):
        chunk, total = _sig_chunk(res, len(signature))
        if sig_total is None:
            sig_total = total
        elif total != sig_total:
            raise ValueError("TXSIGCHUNK total size changed mid-stream")
        signature.extend(chunk)
        res = session.call(messages.CKBTxAckSigChunk())

    if not isinstance(res, messages.CKBSphincsPlusMessageSignature):
        raise exceptions.TrezorException(f"Unexpected message {res}")
    if sig_total is None:
        raise ValueError("Device did not stream the SPHINCS+ signature")
    if len(signature) != sig_total:
        raise ValueError(
            f"Incomplete signature stream: {len(signature)} of {sig_total} bytes"
        )

    return SphincsMessageSignature(
        address=res.address,
        public_key=bytes(res.public_key),
        variant=res.variant,
        signature=bytes(signature),
    )


@workflow(capability=messages.Capability.CKB)
def verify_sphincs_message(
    session: "Session",
    address: str,
    public_key: bytes,
    message: AnyStr,
    signature: bytes,
    network: str = "Mainnet",
    variant: int = 49,
    chunkify: bool = False,
) -> bool:
    """Verify a SPHINCS+ message signature on the device.

    The device drives the transfer: it requests each chunk of the signature by
    offset and this function answers from ``signature``.
    """
    try:
        res = session.call(
            messages.CKBSphincsPlusVerifyMessage(
                address=address,
                public_key=public_key,
                message=prepare_message_bytes(message),
                variant=variant,
                network=network,
                signature_total_size=len(signature),
                chunkify=chunkify,
            )
        )

        # A well-behaved device never needs this many; it only stops a runaway
        # device from holding us in the serve loop forever.
        chunks = 0
        while isinstance(res, messages.CKBTxRequest):
            chunks += 1
            if chunks > _MAX_SIG_CHUNKS:
                raise ValueError("Too many signature chunk requests")
            if res.details is None or res.details.signature_offset is None:
                raise ValueError("TXSIGCHUNK request without chunk metadata")
            offset = res.details.signature_offset
            if offset >= len(signature):
                raise ValueError("Device requested a chunk past the signature")
            res = session.call(
                messages.CKBTxAckSigChunk(
                    signature=signature[offset : offset + _SIG_CHUNK_SIZE]
                )
            )

        if not isinstance(res, messages.Success):
            raise exceptions.TrezorException(f"Unexpected message {res}")
        return True
    except exceptions.TrezorFailure:
        return False


@workflow(capability=messages.Capability.CKB)
def sign_sphincs_tx(
    session: "Session",
    inputs: list["messages.CKBCellInput"],
    outputs: list["messages.CKBCellOutput"],
    cell_deps: list["messages.CKBCellDep"] | None = None,
    witnesses: list["messages.CKBTxAckWitness"] | None = None,
    sign_group_input_indices: list[int] | None = None,
    network: str = "Mainnet",
    account_index: int = 0,
    variant: int = 49,
    chunkify: bool = False,
    prev_txs: dict[bytes | str, CkbPrevTx] | None = None,
    header_deps: list[bytes] | None = None,
    headers: list["messages.CKBBlockHeader"] | None = None,
) -> SphincsSignedTx:
    """Sign a CKB transaction with a SPHINCS+ post-quantum key.

    Same streaming protocol and arguments as :func:`sign_tx` (including
    ``header_deps``/``headers`` for Nervos DAO withdrawals), but keyed by
    ``account_index``/``variant`` instead of a BIP-32 path. The ~50 KB witness
    lock is streamed back in TXSIGCHUNK chunks and returned assembled.
    """
    if cell_deps is None:
        cell_deps = []
    prev_tx_map = {_normalize_tx_hash(k): v for k, v in (prev_txs or {}).items()}

    if witnesses is None:
        witnesses = [create_witness_args()]
        witnesses += [create_witness_raw() for _ in range(max(0, len(inputs) - 1))]
    if sign_group_input_indices is None:
        sign_group_input_indices = list(range(len(inputs)))

    res = session.call(
        messages.CKBSphincsPlusSignTx(
            account_index=account_index,
            variant=variant,
            network=network,
            inputs_count=len(inputs),
            outputs_count=len(outputs),
            cell_deps_count=len(cell_deps),
            witnesses_count=len(witnesses),
            sign_group_input_indices=sign_group_input_indices,
            chunkify=chunkify,
            header_deps=header_deps or [],
        ),
        expect=messages.CKBTxRequest,
    )

    res, witness_lock = _serve_tx_requests(
        session, res, inputs, outputs, cell_deps, witnesses, prev_tx_map, headers
    )
    if res.serialized is None or res.serialized.tx_hash is None:
        raise ValueError("Device did not return the transaction hash")
    if not witness_lock:
        raise ValueError("Device did not stream the SPHINCS+ signature")
    return SphincsSignedTx(
        tx_hash=bytes(res.serialized.tx_hash), witness_lock=witness_lock
    )


def create_cell_input(
    tx_hash: bytes | str,
    index: int,
    since: int = 0,
    dao_deposit_header_index: int | None = None,
    dao_withdraw_header_index: int | None = None,
) -> "messages.CKBCellInput":
    """Create a CKBCellInput message.

    For a Nervos DAO phase-2 withdrawal input, set ``dao_deposit_header_index``
    and ``dao_withdraw_header_index`` to the positions in the transaction's
    ``header_deps`` of the deposit block header and the withdrawing cell's
    including block header; the device then credits the DAO compensation.
    """
    if isinstance(tx_hash, str):
        tx_hash = bytes.fromhex(tx_hash.removeprefix("0x"))

    return messages.CKBCellInput(
        previous_output_tx_hash=tx_hash,
        previous_output_index=index,
        since=since,
        dao_deposit_header_index=dao_deposit_header_index,
        dao_withdraw_header_index=dao_withdraw_header_index,
    )


def create_block_header(
    version: int,
    compact_target: int,
    timestamp: int,
    number: int,
    epoch: int,
    parent_hash: bytes | str,
    transactions_root: bytes | str,
    proposals_hash: bytes | str,
    extra_hash: bytes | str,
    dao: bytes | str,
    nonce: bytes | str,
) -> "messages.CKBBlockHeader":
    """Create a CKBBlockHeader message (used to verify Nervos DAO compensation)."""

    def _b(value: bytes | str) -> bytes:
        if isinstance(value, str):
            return bytes.fromhex(value.removeprefix("0x"))
        return bytes(value)

    return messages.CKBBlockHeader(
        version=version,
        compact_target=compact_target,
        timestamp=timestamp,
        number=number,
        epoch=epoch,
        parent_hash=_b(parent_hash),
        transactions_root=_b(transactions_root),
        proposals_hash=_b(proposals_hash),
        extra_hash=_b(extra_hash),
        dao=_b(dao),
        nonce=_b(nonce),
    )


def create_cell_output(
    capacity: int,
    lock_code_hash: bytes | str,
    lock_hash_type: int,
    lock_args: bytes | str,
    type_code_hash: bytes | str | None = None,
    type_hash_type: int | None = None,
    type_args: bytes | str | None = None,
    data: bytes | None = None,
) -> "messages.CKBCellOutput":
    """Create a CKBCellOutput message."""
    if isinstance(lock_code_hash, str):
        lock_code_hash = bytes.fromhex(lock_code_hash.removeprefix("0x"))
    if isinstance(lock_args, str):
        lock_args = bytes.fromhex(lock_args.removeprefix("0x"))
    if isinstance(type_code_hash, str):
        type_code_hash = bytes.fromhex(type_code_hash.removeprefix("0x"))
    if isinstance(type_args, str):
        type_args = bytes.fromhex(type_args.removeprefix("0x"))

    return messages.CKBCellOutput(
        capacity=capacity,
        lock_code_hash=lock_code_hash,
        lock_hash_type=lock_hash_type,
        lock_args=lock_args,
        type_code_hash=type_code_hash,
        type_hash_type=type_hash_type,
        type_args=type_args,
        data=data,
    )


def create_cell_dep(
    tx_hash: bytes | str,
    index: int,
    dep_type: int,
) -> "messages.CKBCellDep":
    """Create a CKBCellDep message."""
    if isinstance(tx_hash, str):
        tx_hash = bytes.fromhex(tx_hash.removeprefix("0x"))

    return messages.CKBCellDep(
        tx_hash=tx_hash,
        index=index,
        dep_type=dep_type,
    )


def create_witness_args(
    lock_size: int = 65,
    input_type: bytes | None = None,
    output_type: bytes | None = None,
) -> "messages.CKBTxAckWitness":
    """Build the signing witness for a lock-script group (the device blanks its lock field)."""
    return messages.CKBTxAckWitness(
        witness_args=messages.CKBWitnessArgs(
            lock_size=lock_size,
            input_type=input_type,
            output_type=output_type,
        )
    )


def create_witness_raw(raw: bytes = b"") -> "messages.CKBTxAckWitness":
    """Build a non-signing (same-group or trailing) witness from its raw bytes."""
    return messages.CKBTxAckWitness(raw=raw)
