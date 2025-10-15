# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

from . import messages
from .tools import workflow

if TYPE_CHECKING:
    from .client import Session
    from .tools import Address


@workflow()
def get_pubkey(session: "Session", n: "Address") -> bytes:
    return session.call(
        messages.NostrGetPubkey(
            address_n=n,
        ),
        expect=messages.NostrPubkey,
    ).pubkey


@workflow()
def sign_event(
    session: "Session",
    sign_event: messages.NostrSignEvent,
) -> messages.NostrEventSignature:
    return session.call(sign_event, expect=messages.NostrEventSignature)
