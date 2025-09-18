# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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

from __future__ import annotations

import typing as t

import click

from .. import evolu, messages
from . import with_session

if t.TYPE_CHECKING:
    from ..transport.session import Session


@click.group(name="evolu")
def cli() -> None:
    """Evolu commands. Evolu is a local first storage framework. See https://github.com/evoluhq/evolu"""


@cli.command()
@click.argument("proof", type=str)
@with_session
def get_node(
    session: "Session",
    proof: str,
) -> dict[str, str]:
    """Return the SLIP-21 node for Evolu."""
    node: messages.EvoluNode = evolu.get_evolu_node(session, proof=bytes.fromhex(proof))
    return {
        "data": node.data.hex(),
    }


@cli.command()
@click.argument("proof", type=str)
@click.argument("challenge", type=str)
@click.option("--size", "-s", type=int, default=10)
@with_session
def evolu_sign_registration_request(
    session: "Session",
    proof: str,
    challenge: str,
    size: int,
) -> dict[str, str]:
    """Test request that signs a challenge and a size and returns a key."""

    response: messages.EvoluRegistrationRequest = evolu.evolu_sign_registration_request(
        session=session,
        challenge=bytes.fromhex(challenge),
        size=size,
        proof=bytes.fromhex(proof),
    )
    return {
        "certificates": ",".join([cert.hex() for cert in response.certificates]),
        "signature": response.signature.hex(),
    }


@cli.command()
@with_session
def get_delegated_identity_key(
    session: "Session",
) -> dict[str, str]:
    """Request the device for the delegated identity key pair for Evolu."""

    key_pair: messages.EvoluDelegatedIdentityKey = evolu.get_delegated_identity_key(
        session=session
    )
    return {
        "private_key": key_pair.private_key.hex(),
    }
