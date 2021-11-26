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

import json
import re
import sys
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, TextIO, Tuple

import click

from .. import ethereum, tools
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient

try:
    import rlp
    import web3

    HAVE_SIGN_TX = True
except Exception:
    HAVE_SIGN_TX = False


PATH_HELP = "BIP-32 path, e.g. m/44'/60'/0'/0/0"

# fmt: off
ETHER_UNITS = {
    'wei':          1,
    'kwei':         1000,
    'babbage':      1000,
    'femtoether':   1000,
    'mwei':         1000000,
    'lovelace':     1000000,
    'picoether':    1000000,
    'gwei':         1000000000,
    'shannon':      1000000000,
    'nanoether':    1000000000,
    'nano':         1000000000,
    'szabo':        1000000000000,
    'microether':   1000000000000,
    'micro':        1000000000000,
    'finney':       1000000000000000,
    'milliether':   1000000000000000,
    'milli':        1000000000000000,
    'ether':        1000000000000000000,
    'eth':          1000000000000000000,
}
# fmt: on


def _amount_to_int(
    ctx: click.Context, param: Any, value: Optional[str]
) -> Optional[int]:
    if value is None:
        return None
    if value.isdigit():
        return int(value)
    try:
        number, unit = re.match(r"^(\d+(?:.\d+)?)([a-z]+)", value).groups()  # type: ignore ["groups" is not a known member of "None"]
        scale = ETHER_UNITS[unit]
        decoded_number = Decimal(number)
        return int(decoded_number * scale)

    except Exception:
        raise click.BadParameter("Amount not understood")


def _parse_access_list(
    ctx: click.Context, param: Any, value: str
) -> List[ethereum.messages.EthereumAccessList]:
    try:
        return [_parse_access_list_item(val) for val in value]

    except Exception:
        raise click.BadParameter("Access List format invalid")


def _parse_access_list_item(value: str) -> ethereum.messages.EthereumAccessList:
    try:
        arr = value.split(":")
        address, storage_keys = arr[0], arr[1:]
        storage_keys_bytes = [ethereum.decode_hex(key) for key in storage_keys]
        return ethereum.messages.EthereumAccessList(
            address=address, storage_keys=storage_keys_bytes
        )

    except Exception:
        raise click.BadParameter("Access List format invalid")


def _list_units(ctx: click.Context, param: Any, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    maxlen = max(len(k) for k in ETHER_UNITS.keys()) + 1
    for unit, scale in ETHER_UNITS.items():
        click.echo("{:{maxlen}}:  {}".format(unit, scale, maxlen=maxlen))
    ctx.exit()


def _erc20_contract(
    w3: "web3.Web3", token_address: str, to_address: str, amount: int
) -> str:
    min_abi = [
        {
            "name": "transfer",
            "type": "function",
            "constant": False,
            "inputs": [
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"},
            ],
            "outputs": [{"name": "", "type": "bool"}],
        }
    ]
    contract = w3.eth.contract(address=token_address, abi=min_abi)  # type: ignore ["str" cannot be assigned to type "Address | ChecksumAddress | ENS"]
    return contract.encodeABI("transfer", [to_address, amount])


def _format_access_list(
    access_list: List[ethereum.messages.EthereumAccessList],
) -> List[Tuple[bytes, Sequence[bytes]]]:
    return [
        (ethereum.decode_hex(item.address), item.storage_keys) for item in access_list
    ]


#####################
#
# commands start here


@click.group(name="ethereum")
def cli() -> None:
    """Ethereum commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_address(client: "TrezorClient", address: str, show_display: bool) -> str:
    """Get Ethereum address in hex encoding."""
    address_n = tools.parse_path(address)
    return ethereum.get_address(client, address_n, show_display)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_public_node(client: "TrezorClient", address: str, show_display: bool) -> dict:
    """Get Ethereum public node of given path."""
    address_n = tools.parse_path(address)
    result = ethereum.get_public_node(client, address_n, show_display=show_display)
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


@cli.command()
@click.option(
    "-c", "--chain-id", type=int, default=1, help="EIP-155 chain id (replay protection)"
)
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-g", "--gas-limit", type=int, help="Gas limit (required for offline signing)"
)
@click.option(
    "-t",
    "--gas-price",
    help="Gas price (required for offline signing)",
    callback=_amount_to_int,
)
@click.option(
    "-i", "--nonce", type=int, help="Transaction counter (required for offline signing)"
)
@click.option("-d", "--data", help="Data as hex string, e.g. 0x12345678")
@click.option("-p", "--publish", is_flag=True, help="Publish transaction via RPC")
@click.option("-x", "--tx-type", type=int, help="TX type")
@click.option("-t", "--token", help="ERC20 token address")
@click.option(
    "-a",
    "--access-list",
    help="Access List",
    callback=_parse_access_list,
    multiple=True,
)
@click.option("--max-gas-fee", help="Max Gas Fee (EIP1559)", callback=_amount_to_int)
@click.option(
    "--max-priority-fee",
    help="Max Priority Fee (EIP1559)",
    callback=_amount_to_int,
)
@click.option("-e", "--eip2718-type", type=int, help="EIP2718 tx type")
@click.option(
    "--list-units",
    is_flag=True,
    help="List known currency units and exit.",
    is_eager=True,
    callback=_list_units,
    expose_value=False,
)
@click.argument("to_address")
@click.argument("amount", callback=_amount_to_int)
@with_client
def sign_tx(
    client: "TrezorClient",
    chain_id: int,
    address: str,
    amount: int,
    gas_limit: Optional[int],
    gas_price: Optional[int],
    nonce: Optional[int],
    data: Optional[str],
    publish: bool,
    to_address: str,
    tx_type: Optional[int],
    token: Optional[str],
    max_gas_fee: Optional[int],
    max_priority_fee: Optional[int],
    access_list: List[ethereum.messages.EthereumAccessList],
    eip2718_type: Optional[int],
) -> str:
    """Sign (and optionally publish) Ethereum transaction.

    Use TO_ADDRESS as destination address, or set to "" for contract creation.

    Specify a contract address with the --token option to send an ERC20 token.

    You can specify AMOUNT and gas price either as a number of wei,
    or you can use a unit suffix.

    Use the --list-units option to show all known currency units.
    ERC20 token amounts are specified in eth/wei, custom units are not supported.

    If any of gas price, gas limit and nonce is not specified, this command will
    try to connect to an ethereum node and auto-fill these values. You can configure
    the connection with WEB3_PROVIDER_URI environment variable.
    """
    if not HAVE_SIGN_TX:
        click.echo("Ethereum requirements not installed.")
        click.echo("Please run:")
        click.echo()
        click.echo("  pip install web3 rlp")
        sys.exit(1)

    is_eip1559 = eip2718_type == 2
    w3 = web3.Web3()
    if (
        (not is_eip1559 and gas_price is None)
        or any(x is None for x in (gas_limit, nonce))
        or publish
    ) and not w3.isConnected():
        click.echo("Failed to connect to Ethereum node.")
        click.echo(
            "If you want to sign offline, make sure you provide --gas-price, "
            "--gas-limit and --nonce arguments"
        )
        sys.exit(1)

    if data is not None and token is not None:
        click.echo("Can't send tokens and custom data at the same time")
        sys.exit(1)

    address_n = tools.parse_path(address)
    from_address = ethereum.get_address(client, address_n)

    if token:
        data = _erc20_contract(w3, token, to_address, amount)
        to_address = token
        amount = 0

    if data:
        data_bytes = ethereum.decode_hex(data)
    else:
        data_bytes = b""

    if gas_limit is None:
        gas_limit = w3.eth.estimateGas(
            {
                "to": to_address,
                "from": from_address,
                "value": amount,
                "data": f"0x{data_bytes.hex()}",
            }
        )

    if nonce is None:
        nonce = w3.eth.getTransactionCount(from_address)

    assert gas_limit is not None
    assert nonce is not None

    if is_eip1559:
        assert max_gas_fee is not None
        assert max_priority_fee is not None
        sig = ethereum.sign_tx_eip1559(
            client,
            n=address_n,
            nonce=nonce,
            gas_limit=gas_limit,
            to=to_address,
            value=amount,
            data=data_bytes,
            chain_id=chain_id,
            max_gas_fee=max_gas_fee,
            max_priority_fee=max_priority_fee,
            access_list=access_list,
        )
    else:
        if gas_price is None:
            gas_price = w3.eth.gasPrice
        assert gas_price is not None
        sig = ethereum.sign_tx(
            client,
            n=address_n,
            tx_type=tx_type,
            nonce=nonce,
            gas_price=gas_price,
            gas_limit=gas_limit,
            to=to_address,
            value=amount,
            data=data_bytes,
            chain_id=chain_id,
        )

    to = ethereum.decode_hex(to_address)
    if is_eip1559:
        transaction = rlp.encode(
            (
                chain_id,
                nonce,
                max_priority_fee,
                max_gas_fee,
                gas_limit,
                to,
                amount,
                data_bytes,
                _format_access_list(access_list) if access_list is not None else [],
            )
            + sig
        )
    elif tx_type is None:
        transaction = rlp.encode(
            (nonce, gas_price, gas_limit, to, amount, data_bytes) + sig
        )
    else:
        transaction = rlp.encode(
            (tx_type, nonce, gas_price, gas_limit, to, amount, data_bytes) + sig
        )
    if eip2718_type is not None:
        eip2718_prefix = f"{eip2718_type:02x}"
    else:
        eip2718_prefix = ""
    tx_hex = f"0x{eip2718_prefix}{transaction.hex()}"

    if publish:
        tx_hash = w3.eth.sendRawTransaction(tx_hex).hex()
        return f"Transaction published with ID: {tx_hash}"
    else:
        return f"Signed raw transaction:\n{tx_hex}"


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.argument("message")
@with_client
def sign_message(client: "TrezorClient", address: str, message: str) -> Dict[str, str]:
    """Sign message with Ethereum address."""
    address_n = tools.parse_path(address)
    ret = ethereum.sign_message(client, address_n, message)
    output = {
        "message": message,
        "address": ret.address,
        "signature": f"0x{ret.signature.hex()}",
    }
    return output


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "--metamask-v4-compat/--no-metamask-v4-compat",
    default=True,
    help="Be compatible with Metamask's signTypedData_v4 implementation",
)
@click.argument("file", type=click.File("r"))
@with_client
def sign_typed_data(
    client: "TrezorClient", address: str, metamask_v4_compat: bool, file: TextIO
) -> Dict[str, str]:
    """Sign typed data (EIP-712) with Ethereum address.

    Currently NOT supported:
    - arrays of arrays
    - recursive structs
    """
    address_n = tools.parse_path(address)
    data = json.loads(file.read())
    ret = ethereum.sign_typed_data(
        client, address_n, data, metamask_v4_compat=metamask_v4_compat
    )
    output = {
        "address": ret.address,
        "signature": f"0x{ret.signature.hex()}",
    }
    return output


@cli.command()
@click.argument("address")
@click.argument("signature")
@click.argument("message")
@with_client
def verify_message(
    client: "TrezorClient", address: str, signature: str, message: str
) -> bool:
    """Verify message signed with Ethereum address."""
    signature_bytes = ethereum.decode_hex(signature)
    return ethereum.verify_message(client, address, signature_bytes, message)
