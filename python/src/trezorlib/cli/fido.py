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

import click

from .. import fido
from . import with_client

ALGORITHM_NAME = {-7: "ES256 (ECDSA w/ SHA-256)", -8: "EdDSA"}

CURVE_NAME = {1: "P-256 (secp256r1)", 6: "Ed25519"}


@click.group(name="fido")
def cli():
    """FIDO2, U2F and WebAuthN management commands."""


@cli.group()
def credentials():
    """Manage FIDO2 resident credentials."""


@credentials.command(name="list")
@with_client
def credentials_list(client):
    """List all resident credentials on the device."""
    creds = fido.list_credentials(client)
    for cred in creds:
        click.echo("")
        click.echo("WebAuthn credential at index {}:".format(cred.index))
        if cred.rp_id is not None:
            click.echo("  Relying party ID:       {}".format(cred.rp_id))
        if cred.rp_name is not None:
            click.echo("  Relying party name:     {}".format(cred.rp_name))
        if cred.user_id is not None:
            click.echo("  User ID:                {}".format(cred.user_id.hex()))
        if cred.user_name is not None:
            click.echo("  User name:              {}".format(cred.user_name))
        if cred.user_display_name is not None:
            click.echo("  User display name:      {}".format(cred.user_display_name))
        if cred.creation_time is not None:
            click.echo("  Creation time:          {}".format(cred.creation_time))
        if cred.hmac_secret is not None:
            click.echo("  hmac-secret enabled:    {}".format(cred.hmac_secret))
        if cred.use_sign_count is not None:
            click.echo("  Use signature counter:  {}".format(cred.use_sign_count))
        if cred.algorithm is not None:
            algorithm = ALGORITHM_NAME.get(cred.algorithm, cred.algorithm)
            click.echo("  Algorithm:              {}".format(algorithm))
        if cred.curve is not None:
            curve = CURVE_NAME.get(cred.curve, cred.curve)
            click.echo("  Curve:                  {}".format(curve))
        click.echo("  Credential ID:          {}".format(cred.id.hex()))

    if not creds:
        click.echo("There are no resident credentials stored on the device.")


@credentials.command(name="add")
@click.argument("hex_credential_id")
@with_client
def credentials_add(client, hex_credential_id):
    """Add the credential with the given ID as a resident credential.

    HEX_CREDENTIAL_ID is the credential ID as a hexadecimal string.
    """
    return fido.add_credential(client, bytes.fromhex(hex_credential_id))


@credentials.command(name="remove")
@click.option(
    "-i", "--index", required=True, type=click.IntRange(0, 99), help="Credential index."
)
@with_client
def credentials_remove(client, index):
    """Remove the resident credential at the given index."""
    return fido.remove_credential(client, index)


#
# FIDO counter operations
#


@cli.group()
def counter():
    """Get or set the FIDO/U2F counter value."""


@counter.command(name="set")
@click.argument("counter", type=int)
@with_client
def counter_set(client, counter):
    """Set FIDO/U2F counter value."""
    return fido.set_counter(client, counter)


@counter.command(name="get-next")
@with_client
def counter_get_next(client):
    """Get-and-increase value of FIDO/U2F counter.

    FIDO counter value cannot be read directly. On each U2F exchange, the counter value
    is returned and atomically increased. This command performs the same operation
    and returns the counter value.
    """
    return fido.get_next_counter(client)
