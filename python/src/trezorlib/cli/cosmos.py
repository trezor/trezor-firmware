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
import sys
from typing import TYPE_CHECKING, Any, NoReturn, TextIO

import click

from .. import cosmos
from .. import messages as proto_messages
from .. import tools
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient

PATH_HELP = "BIP-32 path, e.g. m/44h/118h/0h/0/0"
CHAIN_ID_HELP = "Cosmos chain id, e.g. cosmoshub-4"
PREFIX_HELP = "Bech32 prefix, e.g. cosmos"
ACCOUNT_NUMBER_HELP = "Account number"
SEQUENCE_HELP = "Sequence"


def _print_cosmos_dependencies_and_die() -> NoReturn:
    click.echo("Cosmos requirements not installed.")
    click.echo("Please run:")
    click.echo()
    click.echo("  pip install trezor[cosmos]")
    sys.exit(1)


def _validate_tx_json(tx_json: Any) -> dict[str, Any]:
    if not isinstance(tx_json, dict):
        raise click.ClickException("Invalid transaction format: expected a JSON object")

    body = tx_json.get("body")
    if not isinstance(body, dict):
        raise click.ClickException("Invalid transaction format: missing 'body' field")

    auth_info = tx_json.get("auth_info")
    if not isinstance(auth_info, dict):
        raise click.ClickException(
            "Invalid transaction format: missing 'auth_info' field"
        )

    fee = auth_info.get("fee")
    if not isinstance(fee, dict):
        raise click.ClickException(
            "Invalid transaction format: missing 'auth_info.fee' field"
        )

    return tx_json


def _require_single_fee_amount(
    fee: proto_messages.CosmosFee,
) -> proto_messages.CosmosCoin:
    if not fee.amount:
        raise click.ClickException("Transaction must specify exactly one fee amount")

    if len(fee.amount) > 1:
        raise click.ClickException("Multiple fee amounts are not supported")

    return fee.amount[0]


def _validate_supported_auth_info(auth_info: Any) -> None:
    if len(auth_info.signer_infos) != 1:
        raise click.ClickException("Transaction must specify exactly one signer")

    if auth_info.fee.payer:
        raise click.ClickException("Fee payer is not supported")

    if auth_info.fee.granter:
        raise click.ClickException("Fee granter is not supported")

    unsupported_fields = sorted(
        field.name
        for field, _ in auth_info.ListFields()
        if field.name not in {"signer_infos", "fee"}
    )
    if unsupported_fields:
        raise click.ClickException(
            "Unsupported auth_info fields: " + ", ".join(unsupported_fields)
        )


def _validate_supported_signer_info(
    signer_info: Any,
    *,
    expected_sequence: int,
    expected_public_key: bytes,
    pubkey_cls: Any,
) -> None:
    signer_mode_info = getattr(signer_info, "mode_info", None)
    if signer_mode_info is None:
        raise click.ClickException("Signer mode_info is required")

    signer_mode_single = getattr(signer_mode_info, "single", None)
    if signer_mode_single is None or getattr(signer_mode_single, "mode", None) != 1:
        raise click.ClickException("Signer mode_info must use SIGN_MODE_DIRECT")

    signer_public_key = getattr(signer_info, "public_key", None)
    if signer_public_key is None:
        raise click.ClickException("Signer public_key is required")

    if signer_public_key.type_url != "/cosmos.crypto.secp256k1.PubKey":
        raise click.ClickException(
            "Signer public_key must use /cosmos.crypto.secp256k1.PubKey"
        )

    signer_pubkey = pubkey_cls()
    try:
        signer_pubkey.ParseFromString(signer_public_key.value)
    except Exception as exc:
        raise click.ClickException("Signer public_key is invalid") from exc

    if signer_pubkey.key != expected_public_key:
        raise click.ClickException(
            "Signer public_key does not match the requested address"
        )

    if signer_info.sequence != expected_sequence:
        raise click.ClickException("Signer sequence does not match --sequence")


def _build_supported_auth_info(
    *,
    auth_info_cls: type,
    any_cls: type,
    pubkey_cls: type,
    fee: Any,
    public_key: bytes,
    sequence: int,
) -> Any:
    auth_info = auth_info_cls()
    signer_info = auth_info.signer_infos.add()

    signer_pubkey = any_cls()
    signer_pubkey.type_url = "/cosmos.crypto.secp256k1.PubKey"
    signer_pubkey.value = pubkey_cls(key=public_key).SerializeToString()

    signer_info.public_key.CopyFrom(signer_pubkey)
    signer_info.mode_info.single.mode = 1
    signer_info.sequence = sequence

    auth_info.fee.CopyFrom(fee)

    return auth_info


@click.group(name="cosmos")
def cli() -> None:
    """Cosmos commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-p", "--prefix", required=True, help=PREFIX_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_address(
    client: "TrezorClient", address: str, prefix: str, show_display: bool
) -> str:
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
    return json.dumps(
        {
            "@type": res.key_type,
            "key": base64.b64encode(res.value).decode("utf-8"),
        }
    )


@cli.command()
@click.argument("file", type=click.File("r"))
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-c", "--chain-id", required=True, help=CHAIN_ID_HELP)
@click.option(
    "-a",
    "--account-number",
    required=True,
    help=ACCOUNT_NUMBER_HELP,
    type=click.IntRange(min=0),
)
@click.option(
    "-s",
    "--sequence",
    required=True,
    help=SEQUENCE_HELP,
    type=click.IntRange(min=0),
)
@with_client
def sign_transaction(
    client: "TrezorClient",
    file: TextIO,
    address: str,
    chain_id: str,
    account_number: int,
    sequence: int,
) -> str:
    """Sign Cosmos transaction."""
    try:
        from cosmpy.protos.cosmos.crypto.secp256k1.keys_pb2 import PubKey
        from cosmpy.protos.cosmos.tx.v1beta1.tx_pb2 import AuthInfo, SignDoc, Tx
        from google.protobuf.any_pb2 import Any as ProtoAny
        from google.protobuf.json_format import MessageToJson, ParseDict, ParseError
    except ModuleNotFoundError:
        _print_cosmos_dependencies_and_die()

    address_n = tools.parse_path(address)
    try:
        tx_json = _validate_tx_json(json.load(file))
    except json.JSONDecodeError as exc:
        raise click.ClickException(
            "Invalid transaction format: malformed JSON"
        ) from exc

    try:
        tx_pb = ParseDict(tx_json, Tx())
    except ParseError as exc:
        raise click.ClickException(f"Invalid transaction format: {exc}") from exc

    _require_single_fee_amount(tx_pb.auth_info.fee)
    _validate_supported_auth_info(tx_pb.auth_info)

    pk = cosmos.get_public_key(client, address_n, False)
    _validate_supported_signer_info(
        tx_pb.auth_info.signer_infos[0],
        expected_sequence=sequence,
        expected_public_key=pk.value,
        pubkey_cls=PubKey,
    )

    auth_info = _build_supported_auth_info(
        auth_info_cls=AuthInfo,
        any_cls=ProtoAny,
        pubkey_cls=PubKey,
        fee=tx_pb.auth_info.fee,
        public_key=pk.value,
        sequence=sequence,
    )

    sd = SignDoc()
    sd.auth_info_bytes = auth_info.SerializeToString()
    sd.body_bytes = tx_pb.body.SerializeToString()
    sd.chain_id = chain_id
    sd.account_number = account_number

    sign_bytes = sd.SerializeToString()

    res = cosmos.sign_tx(client, address_n, sign_bytes)

    signed_tx = Tx()
    signed_tx.body.CopyFrom(tx_pb.body)
    signed_tx.auth_info.CopyFrom(auth_info)
    signed_tx.signatures.append(res.signature)

    return MessageToJson(
        message=signed_tx,
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=True,
        indent=4,
    )
