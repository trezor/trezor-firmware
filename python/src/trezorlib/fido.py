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

from typing import TYPE_CHECKING, List

from . import messages
from .tools import expect

if TYPE_CHECKING:
    from .client import TrezorClient
    from .protobuf import MessageType


@expect(
    messages.WebAuthnCredentials,
    field="credentials",
    ret_type=List[messages.WebAuthnCredential],
)
def list_credentials(client: "TrezorClient") -> "MessageType":
    return client.call(messages.WebAuthnListResidentCredentials())


@expect(messages.Success, field="message", ret_type=str)
def add_credential(client: "TrezorClient", credential_id: bytes) -> "MessageType":
    return client.call(
        messages.WebAuthnAddResidentCredential(credential_id=credential_id)
    )


@expect(messages.Success, field="message", ret_type=str)
def remove_credential(client: "TrezorClient", index: int) -> "MessageType":
    return client.call(messages.WebAuthnRemoveResidentCredential(index=index))


@expect(messages.Success, field="message", ret_type=str)
def set_counter(client: "TrezorClient", u2f_counter: int) -> "MessageType":
    return client.call(messages.SetU2FCounter(u2f_counter=u2f_counter))


@expect(messages.NextU2FCounter, field="u2f_counter", ret_type=int)
def get_next_counter(client: "TrezorClient") -> "MessageType":
    return client.call(messages.GetNextU2FCounter())
