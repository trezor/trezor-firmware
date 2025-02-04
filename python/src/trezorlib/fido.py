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

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from . import messages
from .tools import _return_success

if TYPE_CHECKING:
    from .transport.session import Session


def list_credentials(session: "Session") -> Sequence[messages.WebAuthnCredential]:
    return session.call(
        messages.WebAuthnListResidentCredentials(), expect=messages.WebAuthnCredentials
    ).credentials


def add_credential(session: "Session", credential_id: bytes) -> str | None:
    ret = session.call(
        messages.WebAuthnAddResidentCredential(credential_id=credential_id),
        expect=messages.Success,
    )
    return _return_success(ret)


def remove_credential(session: "Session", index: int) -> str | None:
    ret = session.call(
        messages.WebAuthnRemoveResidentCredential(index=index), expect=messages.Success
    )
    return _return_success(ret)


def set_counter(session: "Session", u2f_counter: int) -> str | None:
    ret = session.call(
        messages.SetU2FCounter(u2f_counter=u2f_counter), expect=messages.Success
    )
    return _return_success(ret)


def get_next_counter(session: "Session") -> int:
    ret = session.call(messages.GetNextU2FCounter(), expect=messages.NextU2FCounter)
    return ret.u2f_counter
