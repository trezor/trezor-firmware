#!/usr/bin/env python2
#
# Copyright (C) 2017 mruddy
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import binascii
from trezorlib.client import TrezorClient
from trezorlib.transport_hid import HidTransport
from trezorlib.tx_api import *
from trezorlib import types_pb2 as types

def main():
    print('Welcome to the user-unfriendly transaction signing tool')
    print('USE AT YOUR OWN RISK')

    coin = raw_input('Which coin {Bitcoin, Testnet, Litecoin}? ').strip()

    if coin not in {'Bitcoin', 'Testnet', 'Litecoin'}:
        print('not supported')
        exit(1)

    # List all connected TREZORs on USB
    devices = HidTransport.enumerate()

    # Check whether we found any
    if len(devices) == 0:
        print('No TREZOR found')
        return

    # Use first connected device
    transport = HidTransport(devices[0])

    # Creates object for manipulating TREZOR
    client = TrezorClient(transport)

    txapi_lookup = {
        'Bitcoin': TxApiBitcoin,
        'Testnet': TxApiTestnet,
        'Litecoin': TxApiLitecoin
    }

    client.set_tx_api(txapi_lookup[coin])

    inputs = []

    while True:
        prev_in_hash = raw_input('Previous input hash (enter nothing to move on): ').strip()
        if prev_in_hash == '':
            break
        prev_in_vout = raw_input('    Previous input index: ').strip()
        addrn = raw_input("    Node to sign with (e.g.- " + coin + "/0'/0/0): ").strip()
        inputs.append(types.TxInputType(
            prev_hash = binascii.unhexlify(prev_in_hash),
            prev_index = int(prev_in_vout, 10),
            address_n = client.expand_path(addrn)
        ))

    outputs = []

    while True:
        out_addr = raw_input('Pay to address (enter nothing to move on): ').strip()
        if out_addr == '':
            break
        out_amount = raw_input('    Amount (in satoshis): ').strip()
        outputs.append(types.TxOutputType(
            amount = int(out_amount, 10),
            script_type = types.PAYTOADDRESS,
            address = out_addr
        ))

    (signatures, serialized_tx) = client.sign_tx(coin, inputs, outputs)

    print('Signed Transaction:', binascii.hexlify(serialized_tx))

    # note: these api's are useful for checking and sending the output of this tool:
    # https://btc.blockr.io/tx/push -or- https://live.blockcypher.com/btc/pushtx/
    # https://tbtc.blockr.io/tx/push -or- https://live.blockcypher.com/btc-testnet/pushtx/
    # https://ltc.blockr.io/tx/push -or - https://live.blockcypher.com/ltc/pushtx/

    client.close()

if __name__ == '__main__':
    main()
