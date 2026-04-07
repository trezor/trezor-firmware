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

from typing import TYPE_CHECKING, Any

from . import messages
from .tools import workflow

if TYPE_CHECKING:
    from .client import Session
    from .tools import Address


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


@workflow(capability=messages.Capability.Tezos)
def get_authenticated_address(
    session: "Session",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> messages.TezosAddress:
    return session.call(
        messages.TezosGetAddress(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=messages.TezosAddress,
    )


@workflow(capability=messages.Capability.Tezos)
def get_public_key(
    session: "Session",
    address_n: "Address",
    show_display: bool = False,
    chunkify: bool = False,
) -> str:
    return session.call(
        messages.TezosGetPublicKey(
            address_n=address_n, show_display=show_display, chunkify=chunkify
        ),
        expect=messages.TezosPublicKey,
    ).public_key


@workflow(capability=messages.Capability.Tezos)
def sign_tx(
    session: "Session",
    address_n: "Address",
    sign_tx_msg: messages.TezosSignTx,
    chunkify: bool = False,
) -> messages.TezosSignedTx:
    sign_tx_msg.address_n = address_n
    sign_tx_msg.chunkify = chunkify
    return session.call(sign_tx_msg, expect=messages.TezosSignedTx)
