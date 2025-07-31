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

from typing import TYPE_CHECKING, TextIO

import click
import json
import base64

from .. import cosmos, tools
from . import with_client

if TYPE_CHECKING:
    from .. import messages
    from ..client import TrezorClient

PATH_HELP = "BIP-32 path, e.g. m/44h/194h/0h/0/0"
CHAIN_ID_HELP = "Cosmos chain id, e.g. cosmoshub-4"
PREFIX_HELP = "Bech32 prefix, e.g. cosmos"
ACCOUNT_NUMBER_HELP = "Account number"
SEQUENCE_HELP = "Sequence"

@click.group(name="cosmos")
def cli() -> None:
    """Cosmos commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-p", "--prefix", required=True, help=PREFIX_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_address(client: "TrezorClient", address: str, prefix: str, show_display: bool) -> str:
    """Get Cosmos address in bech32 encoding."""
    address_n = tools.parse_path(address)
    res = cosmos.get_address(client, address_n, prefix, show_display)
    return res.address

@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_public_key(client: "TrezorClient", address: str, show_display: bool) -> str:
    """Get Cosmos public key in json encoding."""
    address_n = tools.parse_path(address)
    res = cosmos.get_public_key(client, address_n, show_display)
    return json.dumps({
        '@type': res.type,
        'key': base64.b64encode(res.value).decode("utf-8"),
    })

@cli.command()
@click.argument("file", type=click.File("r"))
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-c", "--chain-id", required=True, help=CHAIN_ID_HELP)
@click.option("-a", "--account-number", required=True, help=ACCOUNT_NUMBER_HELP, type=int)
@click.option("-s", "--sequence", required=True, help=SEQUENCE_HELP, type=int)
@with_client
def sign_transaction(client: "TrezorClient", file: TextIO, address: str, chain_id: str, account_number: int, sequence: int) -> str:
    """Sign Cosmos transaction."""

    from google.protobuf.json_format import ParseDict, MessageToJson
    from cosmpy.protos.cosmos.tx.v1beta1.tx_pb2 import Tx
    from cosmpy.aerial.tx import Transaction, SigningCfg, TxFee
    from cosmpy.aerial.coins import Coin
    from cosmpy.crypto.keypairs import PublicKey
    from cosmpy.protos.cosmos.tx.v1beta1.tx_pb2 import SignDoc
    from cosmpy.protos.cosmos.bank.v1beta1.tx_pb2 import MsgSend # needed to parse the json message

    address_n = tools.parse_path(address)
    tx_json = json.load(file)

    tx_pb = ParseDict(tx_json, Tx(), ignore_unknown_fields=True)

    pk = cosmos.get_public_key(client, address_n, False)

    tx = Transaction()
    tx.seal(
        signing_cfgs=SigningCfg.direct(
            public_key=PublicKey(pk.value),
            sequence_num=sequence
        ),
        fee=TxFee(
            amount=Coin(
                denom=tx_pb.auth_info.fee.amount[0].denom,
                amount=tx_pb.auth_info.fee.amount[0].amount, # XXX: support multiple amounts
            ),
            gas_limit=tx_pb.auth_info.fee.gas_limit,
            granter=tx_pb.auth_info.fee.granter,
            payer=tx_pb.auth_info.fee.payer,
        ),
        memo=tx_pb.body.memo,
        timeout_height=tx_pb.body.timeout_height
    )

    sd = SignDoc()
    sd.auth_info_bytes = tx._tx.auth_info.SerializeToString()
    sd.body_bytes = tx_pb.body.SerializeToString()
    sd.chain_id = chain_id
    sd.account_number = account_number

    sign_bytes = sd.SerializeToString()
    
    res = cosmos.sign_tx(client, address_n, sign_bytes)

    signed_tx = Tx(
        body=tx_pb.body,
        auth_info=tx._tx.auth_info,
        signatures=[res.signature],
    )

    return MessageToJson(
        message=signed_tx,
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=True,
        indent=4,
    )