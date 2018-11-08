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

from . import messages as proto
from .tools import expect

# MAINNET = 0
# TESTNET = 1
# STAGENET = 2
# FAKECHAIN = 3


@expect(proto.MoneroAddress, field="address")
def get_address(client, n, show_display=False, network_type=0):
    return client.call(
        proto.MoneroGetAddress(
            address_n=n, show_display=show_display, network_type=network_type
        )
    )


@expect(proto.MoneroWatchKey)
def get_watch_key(client, n, network_type=0):
    return client.call(proto.MoneroGetWatchKey(address_n=n, network_type=network_type))
