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
import pathlib
import re
import sys
from decimal import Decimal
from typing import (
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Dict,
    List,
    NoReturn,
    Optional,
    Sequence,
    TextIO,
    Tuple,
)

import click

from .. import ethereum, tools
from ..tools import UH_
from . import with_client

if TYPE_CHECKING:
    import web3
    from ..client import TrezorClient

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

# So that we can import the web3 library only when really used and reuse the instance
_WEB3_INSTANCE: Optional["web3.Web3"] = None


def _print_eth_dependencies_and_die() -> NoReturn:
    click.echo("Ethereum requirements not installed.")
    click.echo("Please run:")
    click.echo()
    click.echo("  pip install trezor[ethereum]")
    sys.exit(1)


def _get_web3() -> "web3.Web3":
    global _WEB3_INSTANCE
    if _WEB3_INSTANCE is None:
        try:
            import web3

            _WEB3_INSTANCE = web3.Web3()
        except ModuleNotFoundError:
            _print_eth_dependencies_and_die()

    return _WEB3_INSTANCE


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


def _erc20_contract(token_address: str, to_address: str, amount: int) -> str:
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
    contract = _get_web3().eth.contract(address=token_address, abi=min_abi)
    return contract.encodeABI("transfer", [to_address, amount])


def _format_access_list(
    access_list: List[ethereum.messages.EthereumAccessList],
) -> List[Tuple[bytes, Sequence[bytes]]]:
    return [
        (ethereum.decode_hex(item.address), item.storage_keys) for item in access_list
    ]


def _get_ethereum_definitions(
    definitions_zip: Optional[pathlib.Path] = None,
    network_def_file: Optional[BinaryIO] = None,
    token_def_file: Optional[BinaryIO] = None,
    download_definitions: bool = False,
    chain_id: Optional[int] = None,
    slip44_hardened: Optional[int] = None,
    token_address: Optional[str] = None,
) -> ethereum.messages.EthereumDefinitions:
    count_of_options_used = sum(
        bool(o)
        for o in (
            definitions_zip,
            (network_def_file or token_def_file),
            download_definitions,
        )
    )
    if count_of_options_used > 1:
        raise click.ClickException(
            "More than one mutually exclusive option for definitions was used. See --help for more info."
        )

    slip44 = None
    if slip44_hardened is not None:
        slip44 = UH_(slip44_hardened)

    defs = ethereum.messages.EthereumDefinitions()
    if definitions_zip is not None:
        if chain_id is not None or slip44 is not None:
            defs.encoded_network = ethereum.get_definition_from_zip(
                definitions_zip,
                ethereum.get_network_definition_path(chain_id, slip44),
            )
        if chain_id is not None and token_address is not None:
            defs.encoded_token = ethereum.get_definition_from_zip(
                definitions_zip,
                ethereum.get_token_definition_path(chain_id, token_address),
            )
    elif network_def_file is not None or token_def_file is not None:
        if network_def_file is not None:
            with network_def_file:
                defs.encoded_network = network_def_file.read()
        if token_def_file is not None:
            with token_def_file:
                defs.encoded_token = token_def_file.read()
    elif download_definitions:
        if chain_id is not None or slip44 is not None:
            defs.encoded_network = ethereum.download_from_url(
                ethereum.get_network_definition_url(chain_id, slip44)
            )
        if chain_id is not None and token_address is not None:
            defs.encoded_network = ethereum.download_from_url(
                ethereum.get_token_definition_url(chain_id, token_address)
            )

    return defs


#####################
#
# commands start here


definitions_zip_option = click.option(
    "--definitions-zip",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=pathlib.Path
    ),
    help="Zip file with stored definitions. Zip file could be obtained using command "
    "`trezorctl ethereum download-definitions`. Mutually exclusive with `--network-def`, `--token-def` "
    "and `--download-definitions`.",
)
network_def_option = click.option(
    "--network-def",
    type=click.File(mode="rb"),
    help="Binary file with network definition. Mutually exclusive with `--definitions-zip` and `--download-definitions`.",
)
token_def_options = click.option(
    "--token-def",
    type=click.File(mode="rb"),
    help="Binary file with token definition. Mutually exclusive with `--definitions-zip` and `--download-definitions`.",
)
download_definitions_option = click.option(
    "--download-definitions",
    is_flag=True,
    help="Automatically download required definitions from `data.trezor.io/definitions/???` and use them. "
    "Mutually exclusive with `--definitions-zip`, `--network-def` and `--token-def`.",  # TODO: add link?, replace this ur with function used to download defs
)


@click.group(name="ethereum")
def cli() -> None:
    """Ethereum commands."""


@cli.command()
@click.option(
    "-o",
    "--outfile",
    type=click.Path(
        resolve_path=True, dir_okay=False, writable=True, path_type=pathlib.Path
    ),
    default=f"./{ethereum.DEFS_ZIP_FILENAME}",
    help="File path to use to save downloaded definitions. Existing file will be overwritten!",
)
def download_definitions(outfile: pathlib.Path) -> None:
    """Download all Ethereum network and token definitions stored in zip file
    and save them to `outfile`.
    """

    # TODO: change once we know the urls
    archived_definitions = ethereum.download_from_url(
        ethereum.DEFS_BASE_URL + ethereum.DEFS_ZIP_FILENAME
    )

    # save
    with open(outfile, mode="wb+") as f:
        f.write(archived_definitions)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@definitions_zip_option
@network_def_option
@download_definitions_option
@with_client
def get_address(
    client: "TrezorClient",
    address: str,
    show_display: bool,
    definitions_zip: pathlib.Path,
    network_def: BinaryIO,
    download_definitions: bool,
) -> str:
    """Get Ethereum address in hex encoding."""
    address_n = tools.parse_path(address)
    defs = _get_ethereum_definitions(
        definitions_zip=definitions_zip,
        network_def_file=network_def,
        download_definitions=download_definitions,
        slip44_hardened=address_n[1],
    )
    return ethereum.get_address(client, address_n, show_display, defs.encoded_network)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_public_node(
    client: "TrezorClient",
    address: str,
    show_display: bool,
) -> dict:
    """Get Ethereum public node of given path."""
    address_n = tools.parse_path(address)
    result = ethereum.get_public_node(
        client,
        address_n,
        show_display=show_display,
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
@definitions_zip_option
@network_def_option
@token_def_options
@download_definitions_option
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
    definitions_zip: pathlib.Path,
    network_def: BinaryIO,
    token_def: BinaryIO,
    download_definitions: bool,
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
    try:
        import rlp
    except ImportError:
        _print_eth_dependencies_and_die()

    is_eip1559 = eip2718_type == 2
    if (
        (not is_eip1559 and gas_price is None)
        or any(x is None for x in (gas_limit, nonce))
        or publish
    ) and not _get_web3().isConnected():
        click.echo("Failed to connect to Ethereum node.")
        click.echo(
            "If you want to sign offline, make sure you provide --gas-price, "
            "--gas-limit and --nonce arguments"
        )
        sys.exit(1)

    if data is not None and token is not None:
        click.echo("Can't send tokens and custom data at the same time")
        sys.exit(1)

    defs = _get_ethereum_definitions(
        definitions_zip=definitions_zip,
        network_def_file=network_def,
        token_def_file=token_def,
        download_definitions=download_definitions,
        chain_id=chain_id,
        token_address=to_address,
    )

    address_n = tools.parse_path(address)
    from_address = ethereum.get_address(
        client, address_n, encoded_network=defs.encoded_network
    )

    if token:
        data = _erc20_contract(token, to_address, amount)
        to_address = token
        amount = 0
        # to_address has changed, reload definitions
        defs = _get_ethereum_definitions(
            definitions_zip=definitions_zip,
            network_def_file=network_def,
            token_def_file=token_def,
            download_definitions=download_definitions,
            chain_id=chain_id,
            token_address=to_address,
        )

    if data:
        data_bytes = ethereum.decode_hex(data)
    else:
        data_bytes = b""

    if gas_limit is None:
        gas_limit = _get_web3().eth.estimateGas(
            {
                "to": to_address,
                "from": from_address,
                "value": amount,
                "data": f"0x{data_bytes.hex()}",
            }
        )

    if nonce is None:
        nonce = _get_web3().eth.getTransactionCount(from_address)

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
            definitions=defs,
        )
    else:
        if gas_price is None:
            gas_price = _get_web3().eth.gasPrice
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
            definitions=defs,
        )

    to = ethereum.decode_hex(to_address)

    # NOTE: rlp.encode needs a list input to iterate through all its items,
    # it does not work with a tuple
    if is_eip1559:
        transaction_items = [
            chain_id,
            nonce,
            max_priority_fee,
            max_gas_fee,
            gas_limit,
            to,
            amount,
            data_bytes,
            _format_access_list(access_list) if access_list is not None else [],
            *sig,
        ]
    elif tx_type is None:
        transaction_items = [nonce, gas_price, gas_limit, to, amount, data_bytes, *sig]
    else:
        transaction_items = [
            tx_type,
            nonce,
            gas_price,
            gas_limit,
            to,
            amount,
            data_bytes,
            *sig,
        ]
    transaction = rlp.encode(transaction_items)

    if eip2718_type is not None:
        eip2718_prefix = f"{eip2718_type:02x}"
    else:
        eip2718_prefix = ""
    tx_hex = f"0x{eip2718_prefix}{transaction.hex()}"

    if publish:
        tx_hash = _get_web3().eth.sendRawTransaction(tx_hex).hex()
        return f"Transaction published with ID: {tx_hash}"
    else:
        return f"Signed raw transaction:\n{tx_hex}"


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.argument("message")
@definitions_zip_option
@network_def_option
@download_definitions_option
@with_client
def sign_message(
    client: "TrezorClient",
    address: str,
    message: str,
    definitions_zip: pathlib.Path,
    network_def: BinaryIO,
    download_definitions: bool,
) -> Dict[str, str]:
    """Sign message with Ethereum address."""
    address_n = tools.parse_path(address)
    defs = _get_ethereum_definitions(
        definitions_zip=definitions_zip,
        network_def_file=network_def,
        download_definitions=download_definitions,
        slip44_hardened=address_n[1],
    )
    ret = ethereum.sign_message(client, address_n, message, defs.encoded_network)
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
@definitions_zip_option
@network_def_option
@token_def_options
@download_definitions_option
@with_client
def sign_typed_data(
    client: "TrezorClient",
    address: str,
    metamask_v4_compat: bool,
    file: TextIO,
    definitions_zip: pathlib.Path,
    network_def: BinaryIO,
    token_def: BinaryIO,
    download_definitions: bool,
) -> Dict[str, str]:
    """Sign typed data (EIP-712) with Ethereum address.

    Currently NOT supported:
    - arrays of arrays
    - recursive structs
    """
    address_n = tools.parse_path(address)
    data = json.loads(file.read())
    defs = _get_ethereum_definitions(
        definitions_zip=definitions_zip,
        network_def_file=network_def,
        token_def_file=token_def,
        download_definitions=download_definitions,
        slip44_hardened=address_n[1],
    )
    ret = ethereum.sign_typed_data(
        client,
        address_n,
        data,
        metamask_v4_compat=metamask_v4_compat,
        definitions=defs,
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
    client: "TrezorClient",
    address: str,
    signature: str,
    message: str,
) -> bool:
    """Verify message signed with Ethereum address."""
    signature_bytes = ethereum.decode_hex(signature)
    return ethereum.verify_message(client, address, signature_bytes, message)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.argument("domain_hash_hex")
@click.argument("message_hash_hex")
@definitions_zip_option
@network_def_option
@download_definitions_option
@with_client
def sign_typed_data_hash(
    client: "TrezorClient",
    address: str,
    domain_hash_hex: str,
    message_hash_hex: str,
    definitions_zip: pathlib.Path,
    network_def: BinaryIO,
    download_definitions: bool,
) -> Dict[str, str]:
    """
    Sign hash of typed data (EIP-712) with Ethereum address.

    For T1 backward compatibility.

    MESSAGE_HASH_HEX can be set to an empty string '' for domain-only hashes.
    """
    address_n = tools.parse_path(address)
    domain_hash = ethereum.decode_hex(domain_hash_hex)
    message_hash = ethereum.decode_hex(message_hash_hex) if message_hash_hex else None
    defs = _get_ethereum_definitions(
        definitions_zip=definitions_zip,
        network_def_file=network_def,
        download_definitions=download_definitions,
        slip44_hardened=address_n[1],
    )
    ret = ethereum.sign_typed_data_hash(
        client, address_n, domain_hash, message_hash, defs.encoded_network
    )
    output = {
        "domain_hash": domain_hash_hex,
        "message_hash": message_hash_hex,
        "address": ret.address,
        "signature": f"0x{ret.signature.hex()}",
    }
    return output
