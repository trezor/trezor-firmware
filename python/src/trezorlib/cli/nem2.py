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

from .. import nem2, tools

@click.group(name="nem2")
def cli():
    """NEM2 commands."""


@cli.command(help="Get NEM2 Public Key for specified path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/43'/0'/0'/0'")
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def nem2_get_public_key(connect, address, network, show_display):
    """Get NEM address for specified path."""
    client = connect()
    address_n = tools.parse_path(address)
    return nem2.get_public_key(client, address_n, show_display)


@cli.command(help="Sign NEM2 transaction.")
@click.option("-n", "--address", required=True, help="BIP-32 path to signing key")
@click.option("-g", "--generation_hash", required=True, help="NEM2 network generation hash")
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    required=True,
    help="path to json file containing transaction object as per typescript sdk",
)
@click.pass_obj
def nem2_sign_tx(connect, address, generation_hash, file):
    """Sign NEM2 transaction."""
    client = connect()
    address_n = tools.parse_path(address)

    transaction = nem2.sign_tx(client, address_n, generation_hash, json.load(file))

    payload = {
      "payload": transaction.payload.hex(),
      "hash": transaction.hash.hex()
      "signature": transaction.signature.hex()
    }

    return payload

@cli.command(help="Encrypt NEM2 message.")
@click.option("-n", "--address", required=True, help="BIP-32 path to signing key")
@click.option("-r", "--recipient_public_key", required=True, help="Public key of message recipient")
@click.option("-p", "--payload", required=True, help="Plain text message payload")

@click.pass_obj
def nem2_encrypt_message(connect, address, recipient_public_key, payload):
    """Generate an encrypted message payload for the recipient"""
    client = connect()
    address_n = tools.parse_path(address)
    return nem2.encrypt_message(client, address_n, {
      recipientPublicKey: recipient_public_key,
      payload: payload
    })

@cli.command(help="Decrypt NEM2 message.")
@click.option("-n", "--address", required=True, help="BIP-32 path to signing key")
@click.option("-r", "--sender_public_key", required=True, help="Public key of message sender")
@click.option("-p", "--payload", required=True, help="Encrypted message payload as per nem2-sdk")

@click.pass_obj
def nem2_decrypt_message(connect, address, sender_public_key, payload):
    """Decrypt an encrypted message payload from the sender"""
    client = connect()
    address_n = tools.parse_path(address)
    return nem2.decrypt_message(client, address_n, {
      senderPublicKey: sender_public_key,
      payload: payload
    })