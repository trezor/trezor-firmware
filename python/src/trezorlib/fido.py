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

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from . import messages
from .tools import workflow

if TYPE_CHECKING:
    from .client import Session


@workflow()
def list_credentials(session: "Session") -> Sequence[messages.WebAuthnCredential]:
    """List all credentials stored on the device.

    Args:
        session: Session instance

    Returns:
        List of credentials stored on the device.
    """
    return session.call(
        messages.WebAuthnListResidentCredentials(), expect=messages.WebAuthnCredentials
    ).credentials


@workflow()
def add_credential(session: "Session", credential_id: bytes) -> None:
    """Add a credential to the device.

    Args:
        session: Session instance
        credential_id: Credential ID to add

    Returns:
        Success message
    """
    session.call(
        messages.WebAuthnAddResidentCredential(credential_id=credential_id),
        expect=messages.Success,
    )


@workflow()
def remove_credential(session: "Session", index: int) -> None:
    """Remove a credential from the device.

    Args:
        session: Session instance
        index: Index of the credential to remove

    Returns:
        Success message
    """
    session.call(
        messages.WebAuthnRemoveResidentCredential(index=index), expect=messages.Success
    )


@workflow()
def set_counter(session: "Session", u2f_counter: int) -> None:
    """Set the U2F counter.

    Args:
        session: Session instance
        u2f_counter: U2F counter value

    Returns:
        Success message
    """
    session.call(
        messages.SetU2FCounter(u2f_counter=u2f_counter), expect=messages.Success
    )


@workflow()
def get_next_counter(session: "Session") -> int:
    """Get the next U2F counter value.

    This is a get-and-increment operation. Subsequent calls to this function will
    return an ever increasing value. It is not possible to get the current value
    without incrementing it.

    Args:
        session: Session instance

    Returns:
        int: Next U2F counter value
    """
    return session.call(
        messages.GetNextU2FCounter(), expect=messages.NextU2FCounter
    ).u2f_counter
