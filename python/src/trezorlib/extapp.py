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

from typing import TYPE_CHECKING, Union
from pathlib import Path

from . import messages

if TYPE_CHECKING:
    from .transport.session import Session


def load(session: "Session", path: Union[str, Path]) -> bytes:
    """Load an external application onto the device.

    Returns:
        Hash of the loaded app (bytes)
    """
    resp = session.call(
        messages.ExtAppLoad(path=str(path)),
        expect=messages.ExtAppLoaded,
    )
    return bytes(resp.hash or b"")


def run(
    session: "Session",
    hash: bytes,
    fn_id: int,
    data: bytes = b"",
) -> messages.ExtAppResult:
    """Run an external application (starts IPC responder on device).

    Args:
        hash: Hash of the app to run
        fn_id: Function ID to invoke
        data: Serialized function arguments (optional)

    Returns:
        ExtAppResult message from the device
    """
    return session.call(
        messages.ExtAppRun(hash=hash, fn_id=fn_id, data=data),
        expect=messages.ExtAppResult,
    )
