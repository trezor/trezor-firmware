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
    return session.call(
        messages.WebAuthnListResidentCredentials(), expect=messages.WebAuthnCredentials
    ).credentials


@workflow()
def add_credential(session: "Session", credential_id: bytes) -> None:
    session.call(
        messages.WebAuthnAddResidentCredential(credential_id=credential_id),
        expect=messages.Success,
    )


@workflow()
def remove_credential(session: "Session", index: int) -> None:
    session.call(
        messages.WebAuthnRemoveResidentCredential(index=index), expect=messages.Success
    )


@workflow()
def set_counter(session: "Session", u2f_counter: int) -> None:
    session.call(
        messages.SetU2FCounter(u2f_counter=u2f_counter), expect=messages.Success
    )


@workflow()
def get_next_counter(session: "Session") -> int:
    return session.call(
        messages.GetNextU2FCounter(), expect=messages.NextU2FCounter
    ).u2f_counter
