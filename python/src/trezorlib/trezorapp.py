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

from hashlib import sha256
from typing import TYPE_CHECKING

from . import messages

if TYPE_CHECKING:
    from .transport.session import Session


def load(
    session: "Session",
    id: str,
    version: tuple[int, int],
    data: bytes,
    proof: bytes,
    force_reload: bool = False,
) -> int:
    """Load an external application onto the device.

    Returns:
        Instance ID of the loaded app
    """
    hash = None
    if force_reload:
        hash = sha256(data).digest()
    resp = session.call(
        messages.TrezorAppLoad(hash=hash, id=id, version=version, size=len(data))
    )

    # if resp isinstance AppBinaryRequest
    # call AppBinaryAck (header, proof, DEV ONLY root_for_proof)

    while isinstance(resp, messages.DataChunkRequest):
        chunk = data[resp.data_offset : resp.data_offset + resp.data_length]
        resp = session.call(messages.DataChunkAck(data_chunk=chunk))

    resp = messages.TrezorAppLoaded.ensure_isinstance(resp)
    return resp.instance_id
