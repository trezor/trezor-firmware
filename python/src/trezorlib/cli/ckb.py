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

"""CKB (Nervos Network) CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, TextIO

import click

from .. import ckb, tools
from . import with_session

if TYPE_CHECKING:
    from .. import messages
    from ..client import Session


PATH_HELP = "BIP-32 path, e.g. m/44'/309'/0'/0/0"


def _parse_cell_input(inp: Dict) -> "messages.CKBCellInput":
    return ckb.create_cell_input(
        tx_hash=inp["tx_hash"],
        index=inp["index"],
        since=inp.get("since", 0),
    )


def _parse_cell_output(out: Dict) -> "messages.CKBCellOutput":
    return ckb.create_cell_output(
        capacity=out["capacity"],
        lock_code_hash=out["lock_code_hash"],
        lock_hash_type=out["lock_hash_type"],
        lock_args=out["lock_args"],
        type_code_hash=out.get("type_code_hash"),
        type_hash_type=out.get("type_hash_type"),
        type_args=out.get("type_args"),
        data=(
            bytes.fromhex(out["data"].removeprefix("0x")) if out.get("data") else None
        ),
    )


def _parse_cell_dep(dep: Dict) -> "messages.CKBCellDep":
    return ckb.create_cell_dep(
        tx_hash=dep["tx_hash"],
        index=dep["index"],
        dep_type=dep["dep_type"],
    )


def _parse_header_dep(header: str | bytes) -> bytes:
    if isinstance(header, str):
        return bytes.fromhex(header.removeprefix("0x"))
    return bytes(header)


def _parse_prev_tx(prev: Dict) -> "ckb.CkbPrevTx":
    return ckb.create_prev_tx(
        outputs=[_parse_cell_output(o) for o in prev["outputs"]],
        inputs=[_parse_cell_input(i) for i in prev.get("inputs", [])],
        cell_deps=[_parse_cell_dep(d) for d in prev.get("cell_deps", [])],
        version=prev.get("version", 0),
        header_deps=[_parse_header_dep(h) for h in prev.get("header_deps", [])],
    )


@click.group(name="ckb")
def cli() -> None:
    """CKB (Nervos Network) commands."""


@cli.command()
@click.option("-n", "--address", default=ckb.DEFAULT_BIP32_PATH, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.option(
    "--coin",
    type=click.Choice(["Mainnet", "Testnet"]),
    required=True,
    help="Network: Mainnet or Testnet",
)
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def get_address(
    session: "Session",
    address: str,
    show_display: bool,
    coin: str,
    chunkify: bool,
) -> str:
    """Get CKB address for specified path."""
    address_n = tools.parse_path(address)
    return ckb.get_address(
        session,
        address_n,
        show_display=show_display,
        network=coin,
        chunkify=chunkify,
    )


@cli.command()
@click.option("-n", "--address", default=ckb.DEFAULT_BIP32_PATH, help=PATH_HELP)
@click.option(
    "--coin",
    type=click.Choice(["Mainnet", "Testnet"]),
    default="Mainnet",
    help="Network (default: Mainnet)",
)
@click.option("-C", "--chunkify", is_flag=True)
@click.argument("message")
@with_session
def sign_message(
    session: "Session",
    address: str,
    coin: str,
    chunkify: bool,
    message: str,
) -> Dict[str, str]:
    """Sign message with CKB address."""
    address_n = tools.parse_path(address)
    ret = ckb.sign_message(session, address_n, message, network=coin, chunkify=chunkify)
    return {
        "message": message,
        "address": ret.address,
        "signature": f"0x{ret.signature.hex()}",
    }


@cli.command()
@click.option(
    "--coin",
    type=click.Choice(["Mainnet", "Testnet"]),
    default="Mainnet",
    help="Network (default: Mainnet)",
)
@click.option("-C", "--chunkify", is_flag=True)
@click.argument("address")
@click.argument("signature")
@click.argument("message")
@with_session
def verify_message(
    session: "Session",
    coin: str,
    chunkify: bool,
    address: str,
    signature: str,
    message: str,
) -> bool:
    """Verify message signed with CKB address."""
    signature_bytes = bytes.fromhex(signature.removeprefix("0x"))
    return ckb.verify_message(
        session, address, signature_bytes, message, network=coin, chunkify=chunkify
    )


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "--coin",
    type=click.Choice(["Mainnet", "Testnet"]),
    default="Mainnet",
    help="Network (default: Mainnet)",
)
@click.option("-C", "--chunkify", is_flag=True)
@click.argument("json_file", type=click.File("r"))
@with_session
def sign_tx(
    session: "Session",
    address: str,
    coin: str,
    chunkify: bool,
    json_file: TextIO,
) -> str:
    """Sign CKB transaction from a JSON file (must include a ``prev_txs`` map)."""
    import json

    address_n = tools.parse_path(address)
    tx_data = json.load(json_file)

    inputs = [_parse_cell_input(inp) for inp in tx_data.get("inputs", [])]
    outputs = [_parse_cell_output(out) for out in tx_data.get("outputs", [])]
    cell_deps = [_parse_cell_dep(dep) for dep in tx_data.get("cell_deps", [])]
    prev_txs = {
        tx_hash: _parse_prev_tx(prev)
        for tx_hash, prev in tx_data.get("prev_txs", {}).items()
    }

    result = ckb.sign_tx(
        session,
        address_n,
        inputs=inputs,
        outputs=outputs,
        cell_deps=cell_deps,
        network=coin,
        chunkify=chunkify,
        prev_txs=prev_txs,
    )

    if (
        result.serialized is None
        or result.serialized.signature is None
        or result.serialized.tx_hash is None
    ):
        raise click.ClickException("Device did not return signature data")

    return (
        f"Signature: 0x{result.serialized.signature.hex()}\n"
        f"TX Hash: 0x{result.serialized.tx_hash.hex()}"
    )


@cli.command()
@click.option(
    "-a", "--account-index", type=int, default=0, help="SPHINCS+ account index"
)
@click.option("-v", "--variant", type=int, default=49, help="SPHINCS+ variant (48-59)")
@click.option(
    "--coin",
    type=click.Choice(["Mainnet", "Testnet"]),
    default="Mainnet",
    help="Network (default: Mainnet)",
)
@click.option("-C", "--chunkify", is_flag=True)
@click.argument("message")
@with_session
def sign_sphincs_message(
    session: "Session",
    account_index: int,
    variant: int,
    coin: str,
    chunkify: bool,
    message: str,
) -> str:
    """Sign a message with a CKB SPHINCS+ post-quantum key."""
    res = ckb.sign_sphincs_message(
        session,
        message,
        network=coin,
        account_index=account_index,
        variant=variant,
        chunkify=chunkify,
    )
    return (
        f"Address: {res.address}\n"
        f"Public key: 0x{res.public_key.hex()}\n"
        f"Variant: {res.variant}\n"
        f"Signature: 0x{res.signature.hex()}"
    )


@cli.command()
@click.option("-v", "--variant", type=int, default=49, help="SPHINCS+ variant (48-59)")
@click.option(
    "--coin",
    type=click.Choice(["Mainnet", "Testnet"]),
    default="Mainnet",
    help="Network (default: Mainnet)",
)
@click.option("-C", "--chunkify", is_flag=True)
@click.argument("address")
@click.argument("public_key")
@click.argument("signature")
@click.argument("message")
@with_session
def verify_sphincs_message(
    session: "Session",
    variant: int,
    coin: str,
    chunkify: bool,
    address: str,
    public_key: str,
    signature: str,
    message: str,
) -> bool:
    """Verify a CKB SPHINCS+ message signature on the device."""
    return ckb.verify_sphincs_message(
        session,
        address,
        bytes.fromhex(public_key.removeprefix("0x")),
        message,
        bytes.fromhex(signature.removeprefix("0x")),
        network=coin,
        variant=variant,
        chunkify=chunkify,
    )
