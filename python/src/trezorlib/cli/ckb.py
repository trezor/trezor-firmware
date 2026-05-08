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

from typing import TYPE_CHECKING

import click

from .. import ckb, tools
from . import with_session

if TYPE_CHECKING:
    from ..client import Session


PATH_HELP = "BIP-32 path, e.g. m/44'/309'/0'/0/0"


@click.group(name="ckb")
def cli() -> None:
    """CKB (Nervos Network) commands."""


@cli.command()
@click.option(
    "-n", "--address", default=ckb.DEFAULT_BIP32_PATH, help=PATH_HELP
)
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
    json_file,
) -> str:
    """Sign CKB transaction from JSON file."""
    import json

    address_n = tools.parse_path(address)
    tx_data = json.load(json_file)

    inputs = []
    for inp in tx_data.get("inputs", []):
        inputs.append(ckb.create_cell_input(
            tx_hash=inp["tx_hash"],
            index=inp["index"],
            since=inp.get("since", 0),
        ))

    outputs = []
    for out in tx_data.get("outputs", []):
        outputs.append(ckb.create_cell_output(
            capacity=out["capacity"],
            lock_code_hash=out["lock_code_hash"],
            lock_hash_type=out["lock_hash_type"],
            lock_args=out["lock_args"],
            type_code_hash=out.get("type_code_hash"),
            type_hash_type=out.get("type_hash_type"),
            type_args=out.get("type_args"),
            data=bytes.fromhex(out["data"].removeprefix("0x")) if out.get("data") else None,
        ))

    cell_deps = []
    for dep in tx_data.get("cell_deps", []):
        cell_deps.append(ckb.create_cell_dep(
            tx_hash=dep["tx_hash"],
            index=dep["index"],
            dep_type=dep["dep_type"],
        ))

    fee = tx_data.get("fee")

    result = ckb.sign_tx(
        session,
        address_n,
        inputs=inputs,
        outputs=outputs,
        cell_deps=cell_deps,
        network=coin,
        fee=fee,
        chunkify=chunkify,
    )

    if result.serialized is None or result.serialized.signature is None or result.serialized.tx_hash is None:
        raise click.ClickException("Device did not return signature data")

    return (
        f"Signature: 0x{result.serialized.signature.hex()}\n"
        f"TX Hash: 0x{result.serialized.tx_hash.hex()}"
    )
