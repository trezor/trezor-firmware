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

import base64
import json
from typing import TYPE_CHECKING, Dict, List, Optional, TextIO, Tuple

import click
import construct as c

from .. import btc, messages, protobuf, tools
from . import ChoiceType, with_client

if TYPE_CHECKING:
    from ..client import TrezorClient

PURPOSE_BIP44 = 44
PURPOSE_BIP48 = 48
PURPOSE_BIP49 = 49
PURPOSE_BIP84 = 84
PURPOSE_BIP86 = 86
PURPOSE_SLIP25 = 10025

INPUT_SCRIPTS = {
    "address": messages.InputScriptType.SPENDADDRESS,
    "segwit": messages.InputScriptType.SPENDWITNESS,
    "p2shsegwit": messages.InputScriptType.SPENDP2SHWITNESS,
    "taproot": messages.InputScriptType.SPENDTAPROOT,
    "pkh": messages.InputScriptType.SPENDADDRESS,
    "wpkh": messages.InputScriptType.SPENDWITNESS,
    "sh-wpkh": messages.InputScriptType.SPENDP2SHWITNESS,
    "tr": messages.InputScriptType.SPENDTAPROOT,
}

OUTPUT_SCRIPTS = {
    "address": messages.OutputScriptType.PAYTOADDRESS,
    "segwit": messages.OutputScriptType.PAYTOWITNESS,
    "p2shsegwit": messages.OutputScriptType.PAYTOP2SHWITNESS,
    "taproot": messages.OutputScriptType.PAYTOTAPROOT,
    "pkh": messages.OutputScriptType.PAYTOADDRESS,
    "wpkh": messages.OutputScriptType.PAYTOWITNESS,
    "sh-wpkh": messages.OutputScriptType.PAYTOP2SHWITNESS,
    "tr": messages.OutputScriptType.PAYTOTAPROOT,
}

BIP_PURPOSE_TO_DEFAULT_SCRIPT_TYPE = {
    PURPOSE_BIP44: messages.InputScriptType.SPENDADDRESS,
    PURPOSE_BIP49: messages.InputScriptType.SPENDP2SHWITNESS,
    PURPOSE_BIP84: messages.InputScriptType.SPENDWITNESS,
    PURPOSE_BIP86: messages.InputScriptType.SPENDTAPROOT,
    PURPOSE_SLIP25: messages.InputScriptType.SPENDTAPROOT,
}

SCRIPT_TYPE_TO_BIP_PURPOSES = {
    messages.InputScriptType.SPENDADDRESS: (PURPOSE_BIP44,),
    messages.InputScriptType.SPENDP2SHWITNESS: (PURPOSE_BIP49,),
    messages.InputScriptType.SPENDWITNESS: (PURPOSE_BIP84,),
    messages.InputScriptType.SPENDTAPROOT: (PURPOSE_BIP86, PURPOSE_SLIP25),
}

ACCOUNT_TYPE_TO_BIP_PURPOSE = {
    "bip44": PURPOSE_BIP44,
    "bip49": PURPOSE_BIP49,
    "bip84": PURPOSE_BIP84,
    "bip86": PURPOSE_BIP86,
    "slip25": PURPOSE_SLIP25,
}

BIP48_SCRIPT_TYPES = {
    tools.H_(0): messages.InputScriptType.SPENDMULTISIG,
    tools.H_(1): messages.InputScriptType.SPENDP2SHWITNESS,
    tools.H_(2): messages.InputScriptType.SPENDWITNESS,
}

DEFAULT_COIN = "Bitcoin"


XpubStruct = c.Struct(
    "version" / c.Int32ub,
    "depth" / c.Int8ub,
    "fingerprint" / c.Int32ub,
    "child_num" / c.Int32ub,
    "chain_code" / c.Bytes(32),
    "key" / c.Bytes(33),
    c.Terminated,
)


def xpub_deserialize(xpubstr: str) -> Tuple[str, messages.HDNodeType]:
    xpub_bytes = tools.b58check_decode(xpubstr)
    data = XpubStruct.parse(xpub_bytes)
    if data.key[0] == 0:
        private_key = data.key[1:]
        public_key = None
    else:
        public_key = data.key
        private_key = None

    node = messages.HDNodeType(
        depth=data.depth,
        fingerprint=data.fingerprint,
        child_num=data.child_num,
        chain_code=data.chain_code,
        public_key=public_key,  # type: ignore [Argument of type "Unknown | None" cannot be assigned to parameter "public_key" of type "bytes"]
        private_key=private_key,
    )

    return data.version, node


def guess_script_type_from_path(address_n: List[int]) -> messages.InputScriptType:
    if len(address_n) < 1 or not tools.is_hardened(address_n[0]):
        return messages.InputScriptType.SPENDADDRESS

    purpose = tools.unharden(address_n[0])
    if purpose in BIP_PURPOSE_TO_DEFAULT_SCRIPT_TYPE:
        return BIP_PURPOSE_TO_DEFAULT_SCRIPT_TYPE[purpose]

    if purpose == PURPOSE_BIP48 and len(address_n) >= 4:
        script_type_field = address_n[3]
        if script_type_field in BIP48_SCRIPT_TYPES:
            return BIP48_SCRIPT_TYPES[script_type_field]

    return messages.InputScriptType.SPENDADDRESS


def get_unlock_path(address_n: List[int]) -> Optional[List[int]]:
    if address_n and address_n[0] == tools.H_(10025):
        return address_n[:1]
    return None


@click.group(name="btc")
def cli() -> None:
    """Bitcoin and Bitcoin-like coins commands."""


#
# Address functions
#


@cli.command()
@click.option("-c", "--coin", default=DEFAULT_COIN)
@click.option("-n", "--address", required=True, help="BIP-32 path")
@click.option("-t", "--script-type", type=ChoiceType(INPUT_SCRIPTS))
@click.option("-d", "--show-display", is_flag=True)
@click.option("-x", "--multisig-xpub", multiple=True, help="XPUBs of multisig owners")
@click.option("-m", "--multisig-threshold", type=int, help="Number of signatures")
@click.option(
    "-N",
    "--multisig-suffix-length",
    help="BIP-32 suffix length for multisig",
    type=int,
    default=2,
)
@click.option("-C", "--chunkify", is_flag=True)
@with_client
def get_address(
    client: "TrezorClient",
    coin: str,
    address: str,
    script_type: Optional[messages.InputScriptType],
    show_display: bool,
    multisig_xpub: List[str],
    multisig_threshold: Optional[int],
    multisig_suffix_length: int,
    chunkify: bool,
) -> str:
    """Get address for specified path.

    To obtain a multisig address, provide XPUBs of all signers (including your own) in
    the intended order. All XPUBs should be on the same level. By default, it is assumed
    that the XPUBs are on the account level, and the last two components of --address
    should be derived from all of them.

    For BIP-45 multisig:

    \b
    $ trezorctl btc get-public-node -n m/45h/0
    xpub0101
    $ trezorctl btc get-address -n m/45h/0/0/7 -m 3 -x xpub0101 -x xpub0202 -x xpub0303

    This assumes that the other signers also created xpubs at address "m/45h/i".
    For all the signers, the final keys will be derived with the "/0/7" suffix.

    You can specify a different suffix length by using the -N option. For example, to
    use final xpubs, specify '-N 0'.
    """
    address_n = tools.parse_path(address)
    if script_type is None:
        script_type = guess_script_type_from_path(address_n)

    multisig: Optional[messages.MultisigRedeemScriptType]
    if multisig_xpub:
        if multisig_threshold is None:
            raise click.ClickException("Please specify signature threshold")

        multisig_suffix = address_n[-multisig_suffix_length:]
        nodes = [xpub_deserialize(x)[1] for x in multisig_xpub]
        multisig = messages.MultisigRedeemScriptType(
            nodes=nodes, address_n=multisig_suffix, m=multisig_threshold
        )
        if script_type == messages.InputScriptType.SPENDADDRESS:
            script_type = messages.InputScriptType.SPENDMULTISIG
    else:
        multisig = None

    return btc.get_address(
        client,
        coin,
        address_n,
        show_display,
        script_type=script_type,
        multisig=multisig,
        unlock_path=get_unlock_path(address_n),
        chunkify=chunkify,
    )


@cli.command()
@click.option("-c", "--coin", default=DEFAULT_COIN)
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/0'/0'")
@click.option("-e", "--curve")
@click.option("-t", "--script-type", type=ChoiceType(INPUT_SCRIPTS))
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_public_node(
    client: "TrezorClient",
    coin: str,
    address: str,
    curve: Optional[str],
    script_type: Optional[messages.InputScriptType],
    show_display: bool,
) -> dict:
    """Get public node of given path."""
    address_n = tools.parse_path(address)
    if script_type is None:
        script_type = guess_script_type_from_path(address_n)
    result = btc.get_public_node(
        client,
        address_n,
        ecdsa_curve_name=curve,
        show_display=show_display,
        coin_name=coin,
        script_type=script_type,
        unlock_path=get_unlock_path(address_n),
    )
    return {
        "node": {
            "depth": result.node.depth,
            "fingerprint": "%08x" % result.node.fingerprint,
            "child_num": result.node.child_num,
            "chain_code": result.node.chain_code.hex(),
            "public_key": result.node.public_key.hex(),
        },
        "xpub": result.xpub,
    }


def _append_descriptor_checksum(desc: str) -> str:
    checksum = tools.descriptor_checksum(desc)
    return f"{desc}#{checksum}"


def _get_descriptor(
    client: "TrezorClient",
    coin: Optional[str],
    account: int,
    purpose: Optional[int],
    script_type: Optional[messages.InputScriptType],
    show_display: bool,
) -> str:
    if purpose is None:
        if script_type is None:
            script_type = messages.InputScriptType.SPENDADDRESS
        purpose = SCRIPT_TYPE_TO_BIP_PURPOSES[script_type][0]
    elif script_type is None:
        script_type = BIP_PURPOSE_TO_DEFAULT_SCRIPT_TYPE[purpose]
    else:
        if purpose not in SCRIPT_TYPE_TO_BIP_PURPOSES[script_type]:
            raise ValueError("Invalid script type for account type")

    if script_type == messages.InputScriptType.SPENDADDRESS:
        fmt = "pkh({})"
    elif script_type == messages.InputScriptType.SPENDP2SHWITNESS:
        fmt = "sh(wpkh({}))"
    elif script_type == messages.InputScriptType.SPENDWITNESS:
        fmt = "wpkh({})"
    elif script_type == messages.InputScriptType.SPENDTAPROOT:
        fmt = "tr({})"
    else:
        raise ValueError("Unsupported script type")

    coin = coin or DEFAULT_COIN
    if coin == "Bitcoin":
        coin_type = 0
    elif coin == "Testnet" or coin == "Regtest":
        coin_type = 1
    else:
        raise ValueError("Unsupported coin")

    path = f"m/{purpose}'/{coin_type}'/{account}'"
    if purpose == PURPOSE_SLIP25:
        if script_type == messages.InputScriptType.SPENDTAPROOT:
            path += "/1'"
        else:
            raise ValueError("Unsupported SLIP25 script type")

    n = tools.parse_path(path)
    pub = btc.get_public_node(
        client,
        n,
        show_display=show_display,
        coin_name=coin,
        script_type=script_type,
        ignore_xpub_magic=True,
        unlock_path=get_unlock_path(n),
    )

    fingerprint = pub.root_fingerprint if pub.root_fingerprint is not None else 0
    descriptor = f"[{fingerprint:08x}{path[1:]}]{pub.xpub}/<0;1>/*"
    return _append_descriptor_checksum(fmt.format(descriptor))


@cli.command()
@click.option("-c", "--coin")
@click.option(
    "-n", "--account", required=True, type=int, help="account index (0 = first account)"
)
@click.option("-a", "--account-type", type=ChoiceType(ACCOUNT_TYPE_TO_BIP_PURPOSE))
@click.option("-t", "--script-type", type=ChoiceType(INPUT_SCRIPTS))
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_descriptor(
    client: "TrezorClient",
    coin: Optional[str],
    account: int,
    account_type: Optional[int],
    script_type: Optional[messages.InputScriptType],
    show_display: bool,
) -> str:
    """Get descriptor of given account."""
    try:
        return _get_descriptor(
            client, coin, account, account_type, script_type, show_display
        )
    except ValueError as e:
        raise click.ClickException(str(e))


#
# Signing functions
#


@cli.command()
@click.option("-c", "--coin", is_flag=True, hidden=True, expose_value=False)
@click.option("-C", "--chunkify", is_flag=True)
@click.argument("json_file", type=click.File())
@with_client
def sign_tx(client: "TrezorClient", json_file: TextIO, chunkify: bool) -> None:
    """Sign transaction.

    Transaction data must be provided in a JSON file. See `transaction-format.md` for
    description. You can use `tools/build_tx.py` from the source distribution to build
    the required JSON file interactively:

    $ python3 tools/build_tx.py | trezorctl btc sign-tx -
    """
    data = json.load(json_file)
    coin = data.get("coin_name", DEFAULT_COIN)
    details = data.get("details", {})
    inputs = [
        protobuf.dict_to_proto(messages.TxInputType, i) for i in data.get("inputs", ())
    ]
    outputs = [
        protobuf.dict_to_proto(messages.TxOutputType, output)
        for output in data.get("outputs", ())
    ]
    prev_txes = {
        bytes.fromhex(txid): protobuf.dict_to_proto(messages.TransactionType, tx)
        for txid, tx in data.get("prev_txes", {}).items()
    }

    _, serialized_tx = btc.sign_tx(
        client,
        coin,
        inputs,
        outputs,
        prev_txes=prev_txes,
        chunkify=chunkify,
        **details,
    )

    click.echo()
    click.echo("Signed Transaction:")
    click.echo(serialized_tx.hex())


#
# Message functions
#


@cli.command()
@click.option("-c", "--coin", default=DEFAULT_COIN)
@click.option("-n", "--address", required=True, help="BIP-32 path")
@click.option("-t", "--script-type", type=ChoiceType(INPUT_SCRIPTS))
@click.option(
    "-e",
    "--electrum-compat",
    is_flag=True,
    help="Generate Electrum-compatible signature",
)
@click.argument("message")
@with_client
def sign_message(
    client: "TrezorClient",
    coin: str,
    address: str,
    message: str,
    script_type: Optional[messages.InputScriptType],
    electrum_compat: bool,
) -> Dict[str, str]:
    """Sign message using address of given path."""
    address_n = tools.parse_path(address)
    if script_type is None:
        script_type = guess_script_type_from_path(address_n)
    res = btc.sign_message(
        client, coin, address_n, message, script_type, electrum_compat
    )
    return {
        "message": message,
        "address": res.address,
        "signature": base64.b64encode(res.signature).decode(),
    }


@cli.command()
@click.option("-c", "--coin", default=DEFAULT_COIN)
@click.argument("address")
@click.argument("signature")
@click.argument("message")
@with_client
def verify_message(
    client: "TrezorClient", coin: str, address: str, signature: str, message: str
) -> bool:
    """Verify message."""
    signature_bytes = base64.b64decode(signature)
    return btc.verify_message(client, coin, address, signature_bytes, message)


#
# deprecated interactive signing
# ALL BELOW is legacy code and will be dropped
