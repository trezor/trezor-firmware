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
    from .protobuf import MessageType
    from .transport.session import Session


@expect(
    messages.WebAuthnCredentials,
    field="credentials",
    ret_type=List[messages.WebAuthnCredential],
)
def list_credentials(session: "Session") -> "MessageType":
    return session.call(messages.WebAuthnListResidentCredentials())


@expect(messages.Success, field="message", ret_type=str)
def add_credential(session: "Session", credential_id: bytes) -> "MessageType":
    return session.call(
        messages.WebAuthnAddResidentCredential(credential_id=credential_id)
    )


@expect(messages.Success, field="message", ret_type=str)
def remove_credential(session: "Session", index: int) -> "MessageType":
    return session.call(messages.WebAuthnRemoveResidentCredential(index=index))


@expect(messages.Success, field="message", ret_type=str)
def set_counter(session: "Session", u2f_counter: int) -> "MessageType":
    return session.call(messages.SetU2FCounter(u2f_counter=u2f_counter))


@expect(messages.NextU2FCounter, field="u2f_counter", ret_type=int)
def get_next_counter(session: "Session") -> "MessageType":
    return session.call(messages.GetNextU2FCounter())
