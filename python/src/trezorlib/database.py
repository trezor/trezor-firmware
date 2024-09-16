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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from . import messages
from .tools import expect

if TYPE_CHECKING:
    from .client import TrezorClient
    from .protobuf import MessageType

from .databaselib.time import Time


@dataclass
class DatabaseData:
    identifier: bytes
    global_time: Time
    root_digest: bytes
    signature: bytes


@dataclass
class UpdateData:
    identifier: bytes
    global_time: Time
    signature: bytes


@expect(messages.DatabaseModifyKeyResponse)
def modify_key(
    client: "TrezorClient",
    time: bytes,
    signature: bytes,
    key: str,
    value: Optional[str],
    proof: bytes,
) -> "MessageType":
    return client.call(
        messages.DatabaseModifyKey(
            time,
            signature,
            key,
            value,
            proof,
        )
    )


@expect(messages.DatabaseWipeResponse)
def wipe(client: "TrezorClient") -> "MessageType":
    return client.call(messages.DatabaseWipe())


@expect(messages.Success)
def prove_membership(
    client: "TrezorClient",
    database_time: bytes,
    database_signature: bytes,
    key: str,
    proof: bytes,
) -> "MessageType":
    return client.call(
        messages.DatabaseProveMembership(
            database_time,
            database_signature,
            key,
            proof,
        )
    )


@expect(messages.DatabaseMergeResponse)
def merge(
    client: "TrezorClient",
    database_time: bytes,
    database_signature: bytes,
    key: str,
    value: str,
    proof: bytes,
    update_identifier: bytes,
    update_time: bytes,
    update_signature: bytes,
) -> "MessageType":

    return client.call(
        messages.DatabaseMerge(
            database_time,
            database_signature,
            key,
            value,
            proof,
            update_identifier,
            update_time,
            update_signature,
        )
    )
