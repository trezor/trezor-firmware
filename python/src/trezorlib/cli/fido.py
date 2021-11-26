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

from typing import TYPE_CHECKING

import click

from .. import fido
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient

ALGORITHM_NAME = {-7: "ES256 (ECDSA w/ SHA-256)", -8: "EdDSA"}

CURVE_NAME = {1: "P-256 (secp256r1)", 6: "Ed25519"}


@click.group(name="fido")
def cli() -> None:
    """FIDO2, U2F and WebAuthN management commands."""


@cli.group()
def credentials() -> None:
    """Manage FIDO2 resident credentials."""


@credentials.command(name="list")
@with_client
def credentials_list(client: "TrezorClient") -> None:
    """List all resident credentials on the device."""
    creds = fido.list_credentials(client)
    for cred in creds:
        click.echo("")
        click.echo(f"WebAuthn credential at index {cred.index}:")
        if cred.rp_id is not None:
            click.echo(f"  Relying party ID:       {cred.rp_id}")
        if cred.rp_name is not None:
            click.echo(f"  Relying party name:     {cred.rp_name}")
        if cred.user_id is not None:
            click.echo(f"  User ID:                {cred.user_id.hex()}")
        if cred.user_name is not None:
            click.echo(f"  User name:              {cred.user_name}")
        if cred.user_display_name is not None:
            click.echo(f"  User display name:      {cred.user_display_name}")
        if cred.creation_time is not None:
            click.echo(f"  Creation time:          {cred.creation_time}")
        if cred.hmac_secret is not None:
            click.echo(f"  hmac-secret enabled:    {cred.hmac_secret}")
        if cred.use_sign_count is not None:
            click.echo(f"  Use signature counter:  {cred.use_sign_count}")
        if cred.algorithm is not None:
            algorithm = ALGORITHM_NAME.get(cred.algorithm, cred.algorithm)
            click.echo(f"  Algorithm:              {algorithm}")
        if cred.curve is not None:
            curve = CURVE_NAME.get(cred.curve, cred.curve)
            click.echo(f"  Curve:                  {curve}")
        # TODO: could be made required in WebAuthnCredential
        assert cred.id is not None
        click.echo(f"  Credential ID:          {cred.id.hex()}")

    if not creds:
        click.echo("There are no resident credentials stored on the device.")


@credentials.command(name="add")
@click.argument("hex_credential_id")
@with_client
def credentials_add(client: "TrezorClient", hex_credential_id: str) -> str:
    """Add the credential with the given ID as a resident credential.

    HEX_CREDENTIAL_ID is the credential ID as a hexadecimal string.
    """
    return fido.add_credential(client, bytes.fromhex(hex_credential_id))


@credentials.command(name="remove")
@click.option(
    "-i", "--index", required=True, type=click.IntRange(0, 99), help="Credential index."
)
@with_client
def credentials_remove(client: "TrezorClient", index: int) -> str:
    """Remove the resident credential at the given index."""
    return fido.remove_credential(client, index)


#
# FIDO counter operations
#


@cli.group()
def counter() -> None:
    """Get or set the FIDO/U2F counter value."""


@counter.command(name="set")
@click.argument("counter", type=int)
@with_client
def counter_set(client: "TrezorClient", counter: int) -> str:
    """Set FIDO/U2F counter value."""
    return fido.set_counter(client, counter)


@counter.command(name="get-next")
@with_client
def counter_get_next(client: "TrezorClient") -> int:
    """Get-and-increase value of FIDO/U2F counter.

    FIDO counter value cannot be read directly. On each U2F exchange, the counter value
    is returned and atomically increased. This command performs the same operation
    and returns the counter value.
    """
    return fido.get_next_counter(client)
