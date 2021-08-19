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

from . import exceptions, messages
from .protobuf import dict_to_proto
from .tools import dict_from_camelcase, expect, normalize_nfc


@expect(messages.LiskAddress, field="address")
def get_address(client, n, show_display=False):
    return client.call(messages.LiskGetAddress(address_n=n, show_display=show_display))


@expect(messages.LiskPublicKey)
def get_public_key(client, n, show_display=False):
    return client.call(
        messages.LiskGetPublicKey(address_n=n, show_display=show_display)
    )


@expect(messages.LiskMessageSignature)
def sign_message(client, n, message):
    message = normalize_nfc(message)
    return client.call(messages.LiskSignMessage(address_n=n, message=message))


def verify_message(client, pubkey, signature, message):
    message = normalize_nfc(message)
    try:
        resp = client.call(
            messages.LiskVerifyMessage(
                signature=signature, public_key=pubkey, message=message
            )
        )
    except exceptions.TrezorFailure:
        return False
    return isinstance(resp, messages.Success)


RENAMES = {"lifetime": "life_time", "keysgroup": "keys_group"}


@expect(messages.LiskSignedTx)
def sign_tx(client, n, transaction):
    transaction = dict_from_camelcase(transaction, renames=RENAMES)
    msg = dict_to_proto(messages.LiskTransactionCommon, transaction)
    return client.call(messages.LiskSignTx(address_n=n, transaction=msg))
