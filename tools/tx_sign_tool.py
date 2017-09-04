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
from trezorlib.tx_api import TxApiBitcoin, TxApiTestnet, TxApiLitecoin
from trezorlib import types_pb2 as types

# Python2 vs Python3
try:
    input = raw_input
except NameError:
    pass


def get_client():
    devices = HidTransport.enumerate()    # list all connected TREZORs on USB
    if len(devices) == 0:                 # check whether we found any
        return None
    transport = devices[0]                # use first connected device
    return TrezorClient(transport)        # creates object for communicating with TREZOR


def get_txapi():
    coin = input('Which coin {Bitcoin, Testnet, Litecoin}? ').strip()
    if coin not in {'Bitcoin', 'Testnet', 'Litecoin'}:
        return None, None
    txapi_lookup = {
        'Bitcoin': TxApiBitcoin,
        'Testnet': TxApiTestnet,
        'Litecoin': TxApiLitecoin
    }
    return coin, txapi_lookup[coin]


def main():
    client = get_client()
    if not client:
        print('No TREZOR connected')
        return

    print()
    print('Welcome to the user-unfriendly transaction signing tool')
    print('USE AT YOUR OWN RISK!!!')
    print()

    coin, txapi = get_txapi()
    if not txapi:
        print('Coin not supported')
        return

    client.set_tx_api(txapi)

    inputs = []

    while True:
        print()
        prev_in_hash = input('Previous input hash (empty to move on): ').strip()
        if prev_in_hash == '':
            break
        prev_in_vout = input('Previous input index: ').strip()
        addrn = input("Node path to sign with (e.g.- %s/0'/0/0): " % coin).strip()
        inputs.append(types.TxInputType(
            prev_hash=binascii.unhexlify(prev_in_hash),
            prev_index=int(prev_in_vout, 10),
            address_n=client.expand_path(addrn)
        ))

    outputs = []

    while True:
        print()
        out_addr = input('Pay to address (empty to move on): ').strip()
        if out_addr == '':
            break
        out_amount = input('Amount (in satoshis): ').strip()
        outputs.append(types.TxOutputType(
            amount=int(out_amount, 10),
            script_type=types.PAYTOADDRESS,
            address=out_addr
        ))

    (signatures, serialized_tx) = client.sign_tx(coin, inputs, outputs)

    client.close()

    print()
    print('Signed Transaction:', binascii.hexlify(serialized_tx))

    # note: these api's are useful for checking and sending the output of this tool:
    # https://btc.blockr.io/tx/push -or- https://live.blockcypher.com/btc/pushtx/
    # https://tbtc.blockr.io/tx/push -or- https://live.blockcypher.com/btc-testnet/pushtx/
    # https://ltc.blockr.io/tx/push -or - https://live.blockcypher.com/ltc/pushtx/


if __name__ == '__main__':
    main()
