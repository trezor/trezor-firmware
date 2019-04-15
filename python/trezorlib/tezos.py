# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from . import messages
from .tools import expect


@expect(messages.TezosAddress, field="address")
def get_address(client, address_n, show_display=False):
    return client.call(
        messages.TezosGetAddress(address_n=address_n, show_display=show_display)
    )


@expect(messages.TezosPublicKey, field="public_key")
def get_public_key(client, address_n, show_display=False):
    return client.call(
        messages.TezosGetPublicKey(address_n=address_n, show_display=show_display)
    )


@expect(messages.TezosSignedTx)
def sign_tx(client, address_n, sign_tx_msg):
    sign_tx_msg.address_n = address_n
    return client.call(sign_tx_msg)
