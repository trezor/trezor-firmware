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

from typing import TYPE_CHECKING, Optional

import click

from .. import evolu
from . import with_session

if TYPE_CHECKING:
    from ..transport.session import Session


@click.group(name="evolu")
def cli() -> None:
    """Evolu commands. Evolu is a local first storage framework. See https://github.com/evoluhq/evolu"""


@cli.command()
@click.argument("proof", type=str)
@with_session
def get_node(
    session: Session,
    proof: str,
) -> str:
    """Return the SLIP-21 node for Evolu."""
    proof_bytes = bytes.fromhex(proof)
    return evolu.get_node(session, proof=proof_bytes).hex()


@cli.command()
@click.argument("proof", type=str)
@click.argument("challenge", type=str)
@click.option("--size", "-s", type=int, default=1048576)  # 1 MB
@with_session
def sign_registration_request(
    session: Session,
    proof: str,
    challenge: str,
    size: int,
) -> dict[str, str]:
    """Sign a registration request for this device to be registred at the Quota Manager server."""

    response = evolu.sign_registration_request(
        session=session,
        challenge=bytes.fromhex(challenge),
        size=size,
        proof=bytes.fromhex(proof),
    )
    return {
        "certificates": ",".join([cert.hex() for cert in response.certificate_chain]),
        "signature": response.signature.hex(),
    }


@click.option("--credential", "-c", type=str)
@cli.command()
@with_session
def get_delegated_identity_key(
    session: Session,
    credential: Optional[str] = None,
) -> str:
    """
    Request the delegated identity key of this device.
    This key is used to prove the identity of the device at the Quota Manager server and to prove
    to Trezor that this host has been given trust by the user to manage the Suite Sync.
    """

    thp_credential = bytes.fromhex(credential) if credential else None

    return evolu.get_delegated_identity_key(
        session=session,
        thp_credential=thp_credential,
    ).hex()
