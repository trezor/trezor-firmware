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

from trezorlib import nem


def test_nem_basic():
    transaction = {
        "timeStamp": 76809215,
        "amount": 1000000,
        "fee": 1000000,
        "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
        "type": nem.TYPE_TRANSACTION_TRANSFER,
        "deadline": 76895615,
        "version": (0x98 << 24),
        "message": {"payload": b"hello world".hex(), "type": 1},
        "mosaics": [
            {"mosaicId": {"namespaceId": "nem", "name": "xem"}, "quantity": 1000000}
        ],
    }

    msg = nem.create_sign_tx(transaction)

    # this is basically just a random sampling of expected properties
    assert msg.transaction is not None
    assert msg.transfer is not None
    assert len(msg.transfer.mosaics) == 1
    assert msg.transfer.mosaics[0].namespace == "nem"

    assert msg.aggregate_modification is None
    assert msg.provision_namespace is None
