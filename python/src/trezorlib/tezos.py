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

if TYPE_CHECKING:
    from .client import TrezorClient
    from .tools import Address


def get_address(
    client: "TrezorClient",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> str:
    return client.call(
        messages.TezosGetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=messages.TezosAddress,
    ).address


def get_public_key(
    client: "TrezorClient",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> str:
    return client.call(
        messages.TezosGetPublicKey(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=messages.TezosPublicKey,
    ).public_key


def sign_tx(
    client: "TrezorClient",
    address_n: "Address",
    sign_tx_msg: messages.TezosSignTx,
    chunkify: bool = False,
) -> messages.TezosSignedTx:
    sign_tx_msg.address_n = address_n
    sign_tx_msg.chunkify = chunkify
    return client.call(sign_tx_msg, expect=messages.TezosSignedTx)
