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

    Returns:
        CKBTxRequest with signature and tx_hash when TXFINISHED
    """
    from .messages import CKBTxRequestType

    if cell_deps is None:
        cell_deps = []
    prev_tx_map = {_normalize_tx_hash(k): v for k, v in (prev_txs or {}).items()}

    def _get_prev_tx(tx_hash: bytes | None) -> CkbPrevTx:
        if tx_hash is None:
            raise ValueError("Device requested previous tx without a tx_hash")
        key = _normalize_tx_hash(tx_hash)
        if key not in prev_tx_map:
            raise ValueError(f"Missing previous tx for {key.hex()}")
        return prev_tx_map[key]

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
        ),
        expect=messages.CKBTxRequest,
    )

    while res.request_type != CKBTxRequestType.TXFINISHED:
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
        else:
            raise ValueError(f"Unknown request type: {res.request_type}")

    return res


def create_cell_input(
    tx_hash: bytes | str,
    index: int,
    since: int = 0,
) -> "messages.CKBCellInput":
    """Create a CKBCellInput message."""
    if isinstance(tx_hash, str):
        tx_hash = bytes.fromhex(tx_hash.removeprefix("0x"))

    return messages.CKBCellInput(
        previous_output_tx_hash=tx_hash,
        previous_output_index=index,
        since=since,
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
