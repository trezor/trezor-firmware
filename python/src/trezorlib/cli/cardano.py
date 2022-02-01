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
from typing import TYPE_CHECKING, Optional, TextIO

import click

from .. import cardano, messages, tools
from . import ChoiceType, with_client

if TYPE_CHECKING:
    from ..client import TrezorClient

PATH_HELP = "BIP-32 path to key, e.g. m/44'/1815'/0'/0/0"


@click.group(name="cardano")
def cli() -> None:
    """Cardano commands."""


@cli.command()
@click.argument("file", type=click.File("r"))
@click.option("-f", "--file", "_ignore", is_flag=True, hidden=True, expose_value=False)
@click.option(
    "-s",
    "--signing-mode",
    required=True,
    type=ChoiceType({m.name: m for m in messages.CardanoTxSigningMode}),
)
@click.option(
    "-p", "--protocol-magic", type=int, default=cardano.PROTOCOL_MAGICS["mainnet"]
)
@click.option("-N", "--network-id", type=int, default=cardano.NETWORK_IDS["mainnet"])
@click.option("-t", "--testnet", is_flag=True)
@click.option(
    "-D",
    "--derivation-type",
    type=ChoiceType({m.name: m for m in messages.CardanoDerivationType}),
    default=messages.CardanoDerivationType.ICARUS,
)
@with_client
def sign_tx(
    client: "TrezorClient",
    file: TextIO,
    signing_mode: messages.CardanoTxSigningMode,
    protocol_magic: int,
    network_id: int,
    testnet: bool,
    derivation_type: messages.CardanoDerivationType,
) -> cardano.SignTxResponse:
    """Sign Cardano transaction."""
    transaction = json.load(file)

    if testnet:
        protocol_magic = cardano.PROTOCOL_MAGICS["testnet"]
        network_id = cardano.NETWORK_IDS["testnet"]

    inputs = [cardano.parse_input(input) for input in transaction["inputs"]]
    outputs = [cardano.parse_output(output) for output in transaction["outputs"]]
    fee = transaction["fee"]
    ttl = transaction.get("ttl")
    validity_interval_start = transaction.get("validity_interval_start")
    certificates = [
        cardano.parse_certificate(certificate)
        for certificate in transaction.get("certificates", ())
    ]
    withdrawals = [
        cardano.parse_withdrawal(withdrawal)
        for withdrawal in transaction.get("withdrawals", ())
    ]
    auxiliary_data = cardano.parse_auxiliary_data(transaction.get("auxiliary_data"))
    mint = cardano.parse_mint(transaction.get("mint", ()))
    additional_witness_requests = [
        cardano.parse_additional_witness_request(p)
        for p in transaction["additional_witness_requests"]
    ]

    client.init_device(derive_cardano=True)
    sign_tx_response = cardano.sign_tx(
        client,
        signing_mode,
        inputs,
        outputs,
        fee,
        ttl,
        validity_interval_start,
        certificates,
        withdrawals,
        protocol_magic,
        network_id,
        auxiliary_data,
        mint,
        additional_witness_requests,
        derivation_type=derivation_type,
    )

    sign_tx_response["tx_hash"] = sign_tx_response["tx_hash"].hex()
    sign_tx_response["witnesses"] = [
        {
            "type": witness["type"],
            "pub_key": witness["pub_key"].hex(),
            "signature": witness["signature"].hex(),
            "chain_code": witness["chain_code"].hex()
            if witness["chain_code"] is not None
            else None,
        }
        for witness in sign_tx_response["witnesses"]
    ]
    auxiliary_data_supplement = sign_tx_response.get("auxiliary_data_supplement")
    if auxiliary_data_supplement:
        auxiliary_data_supplement["auxiliary_data_hash"] = auxiliary_data_supplement[
            "auxiliary_data_hash"
        ].hex()
        catalyst_signature = auxiliary_data_supplement.get("catalyst_signature")
        if catalyst_signature:
            auxiliary_data_supplement["catalyst_signature"] = catalyst_signature.hex()
        sign_tx_response["auxiliary_data_supplement"] = auxiliary_data_supplement
    return sign_tx_response


@cli.command()
@click.option("-n", "--address", type=str, default="", help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.option(
    "-t",
    "--address-type",
    type=ChoiceType({m.name: m for m in messages.CardanoAddressType}),
    default="BASE",
)
@click.option("-s", "--staking-address", type=str, default="")
@click.option("-h", "--staking-key-hash", type=str, default=None)
@click.option("-b", "--block_index", type=int, default=None)
@click.option("-x", "--tx_index", type=int, default=None)
@click.option("-c", "--certificate_index", type=int, default=None)
@click.option("--script-payment-hash", type=str, default=None)
@click.option("--script-staking-hash", type=str, default=None)
@click.option(
    "-p", "--protocol-magic", type=int, default=cardano.PROTOCOL_MAGICS["mainnet"]
)
@click.option("-N", "--network-id", type=int, default=cardano.NETWORK_IDS["mainnet"])
@click.option("-e", "--testnet", is_flag=True)
@click.option(
    "-D",
    "--derivation-type",
    type=ChoiceType({m.name: m for m in messages.CardanoDerivationType}),
    default=messages.CardanoDerivationType.ICARUS,
)
@with_client
def get_address(
    client: "TrezorClient",
    address: str,
    address_type: messages.CardanoAddressType,
    staking_address: str,
    staking_key_hash: Optional[str],
    block_index: Optional[int],
    tx_index: Optional[int],
    certificate_index: Optional[int],
    script_payment_hash: Optional[str],
    script_staking_hash: Optional[str],
    protocol_magic: int,
    network_id: int,
    show_display: bool,
    testnet: bool,
    derivation_type: messages.CardanoDerivationType,
) -> str:
    """
    Get Cardano address.

    All address types require the address, address_type, protocol_magic and
    network_id parameters.

    When deriving a base address you can choose to include staking info as
    staking_address or staking_key_hash - one has to be chosen.

    When deriving a pointer address you need to specify the block_index,
    tx_index and certificate_index parameters.

    Byron, enterprise and reward addresses only require the general parameters.
    """
    if testnet:
        protocol_magic = cardano.PROTOCOL_MAGICS["testnet"]
        network_id = cardano.NETWORK_IDS["testnet"]

    staking_key_hash_bytes = cardano.parse_optional_bytes(staking_key_hash)
    script_payment_hash_bytes = cardano.parse_optional_bytes(script_payment_hash)
    script_staking_hash_bytes = cardano.parse_optional_bytes(script_staking_hash)

    address_parameters = cardano.create_address_parameters(
        address_type,
        tools.parse_path(address),
        tools.parse_path(staking_address),
        staking_key_hash_bytes,
        block_index,
        tx_index,
        certificate_index,
        script_payment_hash_bytes,
        script_staking_hash_bytes,
    )

    client.init_device(derive_cardano=True)
    return cardano.get_address(
        client,
        address_parameters,
        protocol_magic,
        network_id,
        show_display,
        derivation_type=derivation_type,
    )


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-D",
    "--derivation-type",
    type=ChoiceType({m.name: m for m in messages.CardanoDerivationType}),
    default=messages.CardanoDerivationType.ICARUS,
)
@with_client
def get_public_key(
    client: "TrezorClient",
    address: str,
    derivation_type: messages.CardanoDerivationType,
) -> messages.CardanoPublicKey:
    """Get Cardano public key."""
    address_n = tools.parse_path(address)
    client.init_device(derive_cardano=True)
    return cardano.get_public_key(client, address_n, derivation_type=derivation_type)


@cli.command()
@click.argument("file", type=click.File("r"))
@click.option(
    "-d",
    "--display-format",
    type=ChoiceType({m.name: m for m in messages.CardanoNativeScriptHashDisplayFormat}),
    default="HIDE",
)
@click.option(
    "-D",
    "--derivation-type",
    type=ChoiceType({m.name: m for m in messages.CardanoDerivationType}),
    default=messages.CardanoDerivationType.ICARUS,
)
@with_client
def get_native_script_hash(
    client: "TrezorClient",
    file: TextIO,
    display_format: messages.CardanoNativeScriptHashDisplayFormat,
    derivation_type: messages.CardanoDerivationType,
) -> messages.CardanoNativeScriptHash:
    """Get Cardano native script hash."""
    native_script_json = json.load(file)
    native_script = cardano.parse_native_script(native_script_json)

    client.init_device(derive_cardano=True)
    return cardano.get_native_script_hash(
        client, native_script, display_format, derivation_type=derivation_type
    )
