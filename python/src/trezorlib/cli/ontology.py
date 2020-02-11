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


@cli.command(help="Sign Ontology transaction.")
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-x",
    "--transaction",
    type=click.File("r"),
    required=True,
    help="Transaction in JSON format",
)
@click.option(
    "-t", "--transfer", type=click.File("r"), help="Transfer in JSON format",
)
@click.option(
    "-w", "--withdraw_ong", type=click.File("r"), help="Withdrawal in JSON format",
)
@click.option(
    "-r", "--register", type=click.File("r"), help="Register in JSON format",
)
@click.option(
    "-a", "--attributes", type=click.File("r"), help="Add attributes in JSON format",
)
@click.pass_obj
def sign_transaction(
    connect, address, transaction, transfer, withdraw_ong, register, attributes
):
    client = connect()
    address_n = tools.parse_path(address)
    transaction = protobuf.dict_to_proto(
        messages.OntologyTransaction, json.load(transaction)
    )

    if transfer is not None:
        msg = protobuf.dict_to_proto(messages.OntologyTransfer, json.load(transfer))
    elif withdraw_ong is not None:
        msg = protobuf.dict_to_proto(
            messages.OntologyWithdrawOng, json.load(withdraw_ong)
        )
    elif register is not None:
        msg = protobuf.dict_to_proto(
            messages.OntologyOntIdRegister, json.load(register)
        )
    elif attributes is not None:
        msg = protobuf.dict_to_proto(
            messages.OntologyOntIdAddAttributes, json.load(attributes)
        )
    else:
        raise RuntimeError(
            "No transaction operation specified, use one of -t, -w, -r or -a options"
        )

    return ontology.sign(client, address_n, transaction, msg).hex()
