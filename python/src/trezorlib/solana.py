# This file is part of the Trezor project.
#
# Copyright (C) 2012-2021 SatoshiLabs and contributors
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

import hashlib

from . import exceptions, messages
from .protobuf import dict_to_proto
from .tools import expect


@expect(messages.SolanaAddress, field="address")
def get_address(client, n, show_display=False):
    msg = messages.SolanaGetAddress(address_n=n, show_display=show_display)
    return client.call(msg)


@expect(messages.SolanaSignedTx)
def sign_tx(client, n, transaction):
    hash = hashlib.sha256(transaction).digest()
    return client.call(messages.SolanaSignTxHash(address_n=n, hash=hash))
