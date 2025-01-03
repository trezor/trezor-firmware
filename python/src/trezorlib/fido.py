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
    from .client import TrezorClient


def list_credentials(client: "TrezorClient") -> Sequence[messages.WebAuthnCredential]:
    return client.call(
        messages.WebAuthnListResidentCredentials(), expect=messages.WebAuthnCredentials
    ).credentials


def add_credential(client: "TrezorClient", credential_id: bytes) -> str | None:
    ret = client.call(
        messages.WebAuthnAddResidentCredential(credential_id=credential_id),
        expect=messages.Success,
    )
    return _return_success(ret)


def remove_credential(client: "TrezorClient", index: int) -> str | None:
    ret = client.call(
        messages.WebAuthnRemoveResidentCredential(index=index), expect=messages.Success
    )
    return _return_success(ret)


def set_counter(client: "TrezorClient", u2f_counter: int) -> str | None:
    ret = client.call(
        messages.SetU2FCounter(u2f_counter=u2f_counter), expect=messages.Success
    )
    return _return_success(ret)


def get_next_counter(client: "TrezorClient") -> int:
    ret = client.call(messages.GetNextU2FCounter(), expect=messages.NextU2FCounter)
    return ret.u2f_counter
