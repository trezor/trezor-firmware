# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

import click

from .. import cardano, messages, tools
from . import with_client

PATH_HELP = "BIP-32 path to key, e.g. m/44'/1815'/0'/0/0"


@click.group(name="cardano")
def cli():
    """Cardano commands."""


@cli.command()
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    required=True,
    help="Transaction in JSON format",
)
@click.option("-N", "--network", type=int, default=1)
@with_client
def sign_tx(client, file, network):
    """Sign Cardano transaction."""
    transaction = json.load(file)

    inputs = [cardano.create_input(input) for input in transaction["inputs"]]
    outputs = [cardano.create_output(output) for output in transaction["outputs"]]
    fee = transaction["fee"]
    ttl = transaction["ttl"]
    certificates = []
    if transaction.get("certificates"):
        certificates = [
            cardano.create_certificate(certificate)
            for certificate in transaction["certificates"]
        ]

    signed_transaction = cardano.sign_tx(
        client, inputs, outputs, fee, ttl, certificates, network
    )

    return {
        "tx_hash": signed_transaction.tx_hash.hex(),
        "tx_body": signed_transaction.tx_body.hex(),
    }


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.option(
    "-t", "--address_type", type=int, default=messages.CardanoAddressType.BASE_ADDRESS
)
@click.option("-N", "--network_id", type=int, default=0)
@click.option("-b", "--block_index", type=int, default=None)
@click.option("-x", "--tx_index", type=int, default=None)
@click.option("-c", "--certificate_index", type=int, default=None)
@click.option("-s", "--staking_key_hash_str", type=str, default=None)
@with_client
def get_address(
    client,
    address,
    show_display,
    address_type,
    network_id,
    block_index,
    tx_index,
    certificate_index,
    staking_key_hash_str,
):
    """Get Cardano address."""
    address_n = tools.parse_path(address)

    if block_index is not None or tx_index is not None or certificate_index is not None:
        certificate_pointer = cardano.create_certificate_pointer(
            block_index, tx_index, certificate_index
        )
    else:
        certificate_pointer = None

    if staking_key_hash_str:
        staking_key_hash = bytes.fromhex(staking_key_hash_str)
    else:
        staking_key_hash = None

    address_parameters = cardano.create_address_parameters(
        address_type, address_n, certificate_pointer, staking_key_hash
    )

    return cardano.get_address(client, address_parameters, show_display, network_id,)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@with_client
def get_public_key(client, address):
    """Get Cardano public key."""
    address_n = tools.parse_path(address)
    return cardano.get_public_key(client, address_n)
