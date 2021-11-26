#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import decimal
import json
from typing import Any, Dict, List, Optional, Tuple

import click
import requests

from trezorlib import btc, messages, tools
from trezorlib.cli import ChoiceType
from trezorlib.cli.btc import INPUT_SCRIPTS, OUTPUT_SCRIPTS
from trezorlib.protobuf import to_dict

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "trezorlib"})

# the following script type mapping is only valid for single-sig Trezor-generated utxos
BITCOIN_CORE_INPUT_TYPES = {
    "pubkeyhash": messages.InputScriptType.SPENDADDRESS,
    "scripthash": messages.InputScriptType.SPENDP2SHWITNESS,
    "witness_v0_keyhash": messages.InputScriptType.SPENDWITNESS,
    "witness_v1_taproot": messages.InputScriptType.SPENDTAPROOT,
}


def echo(*args: Any, **kwargs: Any):
    return click.echo(*args, err=True, **kwargs)


def prompt(*args: Any, **kwargs: Any):
    return click.prompt(*args, err=True, **kwargs)


def _default_script_type(address_n: Optional[List[int]], script_types: Any) -> str:
    script_type = "address"

    if address_n is None:
        pass
    elif address_n[0] == tools.H_(49):
        script_type = "p2shsegwit"
    elif address_n[0] == tools.H_(84):
        script_type = "segwit"

    return script_type
    # return script_types[script_type]


def parse_vin(s: str) -> Tuple[bytes, int]:
    txid, vout = s.split(":")
    return bytes.fromhex(txid), int(vout)


def _get_inputs_interactive(
    blockbook_url: str,
) -> Tuple[List[messages.TxInputType], Dict[str, messages.TransactionType]]:
    inputs: List[messages.TxInputType] = []
    txes: Dict[str, messages.TransactionType] = {}
    while True:
        echo()
        prev = prompt(
            "Previous output to spend (txid:vout)", type=parse_vin, default=""
        )
        if not prev:
            break
        prev_hash, prev_index = prev

        txhash = prev_hash.hex()
        tx_url = blockbook_url + txhash
        r = SESSION.get(tx_url)
        if not r.ok:
            raise click.ClickException(f"Failed to fetch URL: {tx_url}")

        tx_json = r.json(parse_float=decimal.Decimal)
        if "error" in tx_json:
            raise click.ClickException(f"Transaction not found: {txhash}")

        tx = btc.from_json(tx_json)
        txes[txhash] = tx
        try:
            from_address = tx_json["vout"][prev_index]["scriptPubKey"]["address"]
            echo(f"From address: {from_address}")
        except Exception:
            pass
        amount = tx.bin_outputs[prev_index].amount
        echo(f"Input amount: {amount}")

        address_n = prompt("BIP-32 path to derive the key", type=tools.parse_path)

        reported_type = tx_json["vout"][prev_index]["scriptPubKey"].get("type")
        if reported_type in BITCOIN_CORE_INPUT_TYPES:
            script_type = BITCOIN_CORE_INPUT_TYPES[reported_type]
            click.echo(f"Script type: {script_type.name}")
        else:
            script_type = prompt(
                "Input type",
                type=ChoiceType(INPUT_SCRIPTS),
                default=_default_script_type(address_n, INPUT_SCRIPTS),
            )
        if isinstance(script_type, str):
            script_type = INPUT_SCRIPTS[script_type]

        sequence = prompt(
            "Sequence Number to use (RBF opt-in enabled by default)",
            type=int,
            default=0xFFFFFFFD,
        )

        new_input = messages.TxInputType(
            address_n=address_n,
            prev_hash=prev_hash,
            prev_index=prev_index,
            amount=amount,
            script_type=script_type,
            sequence=sequence,
        )

        inputs.append(new_input)

    return inputs, txes


def _get_outputs_interactive() -> List[messages.TxOutputType]:
    outputs: List[messages.TxOutputType] = []
    while True:
        echo()
        address = prompt("Output address (for non-change output)", default="")
        if address:
            address_n = None
            script_type = messages.OutputScriptType.PAYTOADDRESS
        else:
            address = None
            address_n = prompt(
                "BIP-32 path (for change output)", type=tools.parse_path, default=""
            )
            if not address_n:
                break
            script_type = prompt(
                "Output type",
                type=ChoiceType(OUTPUT_SCRIPTS),
                default=_default_script_type(address_n, OUTPUT_SCRIPTS),
            )
            if isinstance(script_type, str):
                script_type = OUTPUT_SCRIPTS[script_type]

        amount = prompt("Amount to spend (satoshis)", type=int)

        outputs.append(
            messages.TxOutputType(
                address_n=address_n,
                address=address,
                amount=amount,
                script_type=script_type,
            )
        )

    return outputs


@click.command()
def sign_interactive() -> None:
    coin = prompt("Coin name", default="Bitcoin")
    blockbook_host = prompt("Blockbook server", default="btc1.trezor.io")

    if not SESSION.get(f"https://{blockbook_host}/api/block/1").ok:
        raise click.ClickException("Could not connect to blockbook")

    blockbook_url = f"https://{blockbook_host}/api/tx-specific/"

    inputs, txes = _get_inputs_interactive(blockbook_url)
    outputs = _get_outputs_interactive()

    version = prompt("Transaction version", type=int, default=2)
    lock_time = prompt("Transaction locktime", type=int, default=0)

    result = {
        "coin_name": coin,
        "inputs": [to_dict(i, hexlify_bytes=True) for i in inputs],
        "outputs": [to_dict(o, hexlify_bytes=True) for o in outputs],
        "details": {
            "version": version,
            "lock_time": lock_time,
        },
        "prev_txes": {
            txhash: to_dict(txdata, hexlify_bytes=True)
            for txhash, txdata in txes.items()
        },
    }

    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    sign_interactive()
