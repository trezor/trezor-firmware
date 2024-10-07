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


import json
from typing import TYPE_CHECKING, AnyStr

from . import messages
from .tools import expect

if TYPE_CHECKING:
    from .client import TrezorClient
    from .protobuf import MessageType
    from .tools import Address


@expect(messages.NostrPubkey)
def get_pubkey(
    client: "TrezorClient",
    n: "Address",
) -> "MessageType":
    return client.call(
        messages.NostrGetPubkey(
            address_n=n,
        )
    )


@expect(messages.NostrEventSignature)
def sign_event(
    client: "TrezorClient",
    n: "Address",
    event: AnyStr,
) -> "MessageType":
    event_json = json.loads(event)
    return client.call(
        messages.NostrSignEvent(
            address_n=n,
            created_at=event_json["created_at"],
            kind=event_json["kind"],
            tags=event_json["tags"],
            content=event_json["content"],
        )
    )
