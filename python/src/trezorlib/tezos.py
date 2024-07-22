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

from typing import TYPE_CHECKING

from . import messages
from .tools import expect

if TYPE_CHECKING:
    from .protobuf import MessageType
    from .tools import Address
    from .transport.session import Session


@expect(messages.TezosAddress, field="address", ret_type=str)
def get_address(
    session: "Session",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> "MessageType":
    return session.call(
        messages.TezosGetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        )
    )


@expect(messages.TezosPublicKey, field="public_key", ret_type=str)
def get_public_key(
    session: "Session",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> "MessageType":
    return session.call(
        messages.TezosGetPublicKey(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        )
    )


@expect(messages.TezosSignedTx)
def sign_tx(
    session: "Session",
    address_n: "Address",
    sign_tx_msg: messages.TezosSignTx,
    chunkify: bool = False,
) -> "MessageType":
    sign_tx_msg.address_n = address_n
    sign_tx_msg.chunkify = chunkify
    return session.call(sign_tx_msg)
