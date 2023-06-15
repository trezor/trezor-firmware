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
    """List all credentials stored on the device.

    Args:
        client: TrezorClient instance

    Returns:
        List of credentials stored on the device.
    """
    return client.call(messages.WebAuthnListResidentCredentials())


@expect(messages.Success, field="message", ret_type=str)
def add_credential(client: "TrezorClient", credential_id: bytes) -> "MessageType":
    """Add a credential to the device.

    Args:
        client: TrezorClient instance
        credential_id: Credential ID to add

    Returns:
        str: Success message
    """
    return client.call(
        messages.WebAuthnAddResidentCredential(credential_id=credential_id)
    )


@expect(messages.Success, field="message", ret_type=str)
def remove_credential(client: "TrezorClient", index: int) -> "MessageType":
    """Remove a credential from the device.

    Args:
        client: TrezorClient instance
        index: Index of the credential to remove

    Returns:
        str: Success message
    """
    return client.call(messages.WebAuthnRemoveResidentCredential(index=index))


@expect(messages.Success, field="message", ret_type=str)
def set_counter(client: "TrezorClient", u2f_counter: int) -> "MessageType":
    """Set the U2F counter.

    Args:
        client: TrezorClient instance
        u2f_counter: U2F counter value

    Returns:
        str: Success message
    """
    return client.call(messages.SetU2FCounter(u2f_counter=u2f_counter))


@expect(messages.NextU2FCounter, field="u2f_counter", ret_type=int)
def get_next_counter(client: "TrezorClient") -> "MessageType":
    """Get the next U2F counter value.

    This is a get-and-increment operation. Subsequent calls to this function will
    return an ever increasing value. It is not possible to get the current value
    without incrementing it.

    Args:
        client: TrezorClient instance

    Returns:
        int: Next U2F counter value
    """
    return client.call(messages.GetNextU2FCounter())
