# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

@expect(messages.DebugZcashDiagResponse, field="data")
def diag(client, ins=b"", data=b""):
    """Dangerous temporary function for diagnostic purposes."""
    return client.call(
        messages.DebugZcashDiagRequest(ins=ins, data=data)
    )

@expect(messages.ZcashFullViewingKey, field="fvk")
def get_fvk(client, z_address_n):
    """Returns raw Zcash Orchard Full Viewing Key encoded as:

    ak (32 bytes) || nk (32 bytes) || rivk (32 bytes)
    
    acording to the https://zips.z.cash/protocol/protocol.pdf § 5.6.4.4"""
    return client.call(
        messages.ZcashGetFullViewingKey(
            z_address_n=z_address_n,
        )
    )

@expect(messages.ZcashIncomingViewingKey, field="ivk")
def get_ivk(client, z_address_n):
    """Returns raw Zcash Orchard Incoming Viewing Key encoded as:

    dk (32 bytes) || ivk (32 bytes)
    
    acording to the https://zips.z.cash/protocol/protocol.pdf § 5.6.4.3"""
    return client.call(
        messages.ZcashGetIncomingViewingKey(
            z_address_n=z_address_n,
        )
    )

@expect(messages.ZcashAddress, field="address")
def get_address(
        client,
        t_address_n=[],
        z_address_n=[],
        diversifier_index=0,
        show_display=False
):
    """Returns Zcash address."""
    return client.call(
        messages.ZcashGetAddress(
            t_address_n=t_address_n,
            z_address_n=z_address_n,
            diversifier_index=diversifier_index,
            show_display=show_display,
        )
    )