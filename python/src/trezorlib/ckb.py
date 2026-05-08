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

from typing import TYPE_CHECKING, Any

from . import messages
from .tools import workflow

if TYPE_CHECKING:
    from .tools import Address
    from .client import Session

DEFAULT_BIP32_PATH = "m/44'/309'/0'/0/0"


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
def sign_tx(
    session: "Session",
    address_n: "Address",
    inputs: list["messages.CKBCellInput"],
    outputs: list["messages.CKBCellOutput"],
    cell_deps: list["messages.CKBCellDep"] | None = None,
    network: str = "Mainnet",
    fee: int | None = None,
    chunkify: bool = False,
) -> "messages.CKBTxRequest":
    """
    Sign a CKB transaction using streaming protocol.

    Args:
        session: Trezor session instance
        address_n: BIP-32 path for signing key
        inputs: List of cell inputs to spend
        outputs: List of cell outputs to create
        cell_deps: List of cell dependencies (optional)
        network: "Mainnet" or "Testnet"
        fee: Transaction fee in shannons (optional)
        chunkify: Display addresses in chunks

    Returns:
        CKBTxRequest with signature and tx_hash when TXFINISHED
    """
    from .messages import CKBTxRequestType

    if cell_deps is None:
        cell_deps = []

    res = session.call(
        messages.CKBSignTx(
            address_n=address_n,
            network=network,
            inputs_count=len(inputs),
            outputs_count=len(outputs),
            cell_deps_count=len(cell_deps),
            fee=fee,
            chunkify=chunkify,
        ),
        expect=messages.CKBTxRequest,
    )

    while res.request_type != CKBTxRequestType.TXFINISHED:
        if res.details is None:
            raise ValueError("Device response missing request details")
        idx = res.details.request_index

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
