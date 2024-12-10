# This file is part of the Trezor project.
#
# Copyright (C) 2012-2024 SatoshiLabs and contributors
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

from typing import TYPE_CHECKING, Dict

import click
import json

from .. import nostr, tools
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient

@click.group(name="nostr")
def cli() -> None:
    pass

@cli.command()
@click.option("-n", "--address", required=True, help="BIP-32 path")
@click.argument("event")
@with_client
def sign_event(
    client: "TrezorClient",
    address: str,
    event: str,
) -> Dict[str, str]:
    """Sign an event using address of given path."""

    event_json = json.loads(event)

    address_n = tools.parse_path(address)

    res = nostr.sign_event(
        client,
        address_n,
        event,
    )

    event_json['id'] = res.id.hex()
    event_json['pubkey'] = res.pubkey.hex()
    event_json['sig'] = res.signature.hex()

    return {
        "signed_event": json.dumps(event_json),
    }
