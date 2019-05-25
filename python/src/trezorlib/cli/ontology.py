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

from .. import messages, ontology, protobuf, tools

PATH_HELP = "BIP-32 path to key, e.g. m/44'/888'/0'/0/0"


@click.group(name="ontology")
def cli():
    """Ontology commands."""


@cli.command(help="Get Ontology address for specified path.")
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return ontology.get_address(client, address_n, show_display)


@cli.command(help="Get Ontology public key for specified path.")
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def get_public_key(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    result = ontology.get_public_key(client, address_n, show_display)

    return result.public_key.hex()


@cli.command(help="Sign Ontology transfer.")
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-t",
    "--transaction",
    type=click.File("r"),
    default="-",
    help="Transaction in JSON format",
)
@click.option(
    "-r",
    "--transfer",
    type=click.File("r"),
    default="-",
    help="Transfer in JSON format",
)
@click.pass_obj
def sign_transfer(connect, address, transaction, transfer):
    client = connect()
    address_n = tools.parse_path(address)
    transaction = protobuf.dict_to_proto(
        messages.OntologyTransaction, json.load(transaction)
    )
    transfer = protobuf.dict_to_proto(messages.OntologyTransfer, json.load(transfer))

    result = ontology.sign_transfer(client, address_n, transaction, transfer)

    output = {"payload": result.payload.hex(), "signature": result.signature.hex()}

    return output


@cli.command(help="Sign Ontology withdraw Ong.")
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-t",
    "--transaction",
    type=click.File("r"),
    default="-",
    help="Transaction in JSON format",
)
@click.option(
    "-w",
    "--withdraw_ong",
    type=click.File("r"),
    default="-",
    help="Withdrawal in JSON format",
)
@click.pass_obj
def sign_withdraw_ong(connect, address, transaction, withdraw_ong):
    client = connect()
    address_n = tools.parse_path(address)
    transaction = protobuf.dict_to_proto(
        messages.OntologyTransaction, json.load(transaction)
    )
    withdraw_ong = protobuf.dict_to_proto(
        messages.OntologyWithdrawOng, json.load(withdraw_ong)
    )

    result = ontology.sign_withdrawal(client, address_n, transaction, withdraw_ong)

    output = {"payload": result.payload.hex(), "signature": result.signature.hex()}

    return output


@cli.command(help="Sign Ontology ONT ID Registration.")
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-t",
    "--transaction",
    type=click.File("r"),
    default="-",
    help="Transaction in JSON format",
)
@click.option(
    "-r",
    "--register",
    type=click.File("r"),
    default="-",
    help="Register in JSON format",
)
@click.argument("transaction")
@click.argument("ont_id_register")
@click.pass_obj
def sign_ont_id_register(connect, address, transaction, register):
    client = connect()
    address_n = tools.parse_path(address)
    transaction = protobuf.dict_to_proto(
        messages.OntologyTransaction, json.load(transaction)
    )
    ont_id_register = protobuf.dict_to_proto(
        messages.OntologyOntIdRegister, json.load(register)
    )

    result = ontology.sign_register(client, address_n, transaction, ont_id_register)

    output = {"payload": result.payload.hex(), "signature": result.signature.hex()}

    return output


@cli.command(help="Sign Ontology ONT ID Attributes adding.")
@click.option(
    "-n",
    "--address",
    required=True,
    help="BIP-32 path to signing key, e.g. m/44'/888'/0'/0/0",
)
@click.option(
    "-t",
    "--transaction",
    type=click.File("r"),
    required=True,
    default="-",
    help="Transaction in JSON format",
)
@click.option(
    "-a",
    "--add_attribute",
    type=click.File("r"),
    required=True,
    default="-",
    help="Add attributes in JSON format",
)
@click.pass_obj
def sign_ont_id_add_attributes(connect, address, transaction, add_attribute):
    client = connect()
    address_n = tools.parse_path(address)
    transaction = protobuf.dict_to_proto(
        messages.OntologyTransaction, json.load(transaction)
    )
    ont_id_add_attributes = protobuf.dict_to_proto(
        messages.OntologyOntIdAddAttributes, json.load(add_attribute)
    )
    result = ontology.sign_add_attr(
        client, address_n, transaction, ont_id_add_attributes
    )
    output = {"payload": result.payload.hex(), "signature": result.signature.hex()}

    return output
