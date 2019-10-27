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

import json

from . import messages as proto
from .tools import CallException, expect

TYPE_TRANSACTION_TRANSFER = 0x0101
TYPE_IMPORTANCE_TRANSFER = 0x0801
TYPE_AGGREGATE_MODIFICATION = 0x1001
TYPE_MULTISIG_SIGNATURE = 0x1002
TYPE_MULTISIG = 0x1004
TYPE_PROVISION_NAMESPACE = 0x2001
TYPE_MOSAIC_CREATION = 0x4001
TYPE_MOSAIC_SUPPLY_CHANGE = 0x4002


# ====== Client functions ====== #


@expect(proto.NEM2PublicKey, field="public_key")
def get_public_key(client, n, show_display=False):
    return client.call(
        proto.NEM2GetPublicKey(address_n=n, show_display=show_display)
    )


# @expect(proto.NEM2SignedTx)
# def sign_tx(client, n, transaction):
#     try:
#         msg = create_sign_tx(transaction)
#     except ValueError as e:
#         raise CallException(e.args)

#     assert msg.transaction is not None
#     msg.transaction.address_n = n
#     return client.call(msg)
