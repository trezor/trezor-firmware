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

import json
import typing as t

import click

from .. import messages, nostr, tools
from . import with_client

if t.TYPE_CHECKING:
    from ..client import TrezorClient


PATH_TEMPLATE = "m/44h/1237h/{}h/0/0"


@click.group(name="nostr")
def cli() -> None:
    """Nostr commands."""


@cli.command()
@click.option("-a", "--account", default=0, help="Account index")
@with_client
def get_pubkey(
    client: "TrezorClient",
    account: int,
) -> str:
    """Return the pubkey derived by the given path."""

    address_n = tools.parse_path(PATH_TEMPLATE.format(account))

    return nostr.get_pubkey(
        client,
        address_n,
    ).hex()


@cli.command()
@click.option("-a", "--account", default=0, help="Account index")
@click.argument("event")
@with_client
def sign_event(
    client: "TrezorClient",
    account: int,
    event: str,
) -> dict[str, str]:
    """Sign an event using the key derived by the given path."""

    event_json = json.loads(event)

    address_n = tools.parse_path(PATH_TEMPLATE.format(account))

    res = nostr.sign_event(
        client,
        messages.NostrSignEvent(
            address_n=address_n,
            created_at=event_json["created_at"],
            kind=event_json["kind"],
            tags=[
                messages.NostrTag(
                    key=t[0], value=t[1] if len(t) > 1 else None, extra=t[2:]
                )
                for t in event_json["tags"]
            ],
            content=event_json["content"],
        ),
    )

    event_json["id"] = res.id.hex()
    event_json["pubkey"] = res.pubkey.hex()
    event_json["sig"] = res.signature.hex()

    return {
        "signed_event": event_json,
    }
