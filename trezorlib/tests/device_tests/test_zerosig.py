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

from trezorlib import btc, messages as proto

from ..support.tx_cache import tx_cache
from .common import TrezorTest

TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)


# address_n = [177] < 68
# address_n = [16518] < 66
class TestZerosig(TrezorTest):

    """
    def test_mine_zero_signature(self):
        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC

        inp1 = proto.TxInputType(address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
                             # amount=390000,
                             prev_hash=TXHASH_d5f65e,
                             prev_index=0,
                             )

        msg = self.client._prepare_sign_tx('Bitcoin', [inp1, ], [])

        for n in range(3500, 200000):
            out1 = proto.TxOutputType(address_n=[n],
                                  amount=390000 - 10000,
                                  script_type=proto.OutputScriptType.PAYTOADDRESS,
                                  )
            msg.ClearField('outputs')
            msg.outputs.extend([out1, ])

            tx = self.client.call(msg)

            siglen = tx.serialized_tx[44]
            print(siglen)
            if siglen < 67:
                print("!!!!", n)
                print(tx.serialized_tx.hex())
                return
    """

    def test_one_zero_signature(self):
        self.setup_mnemonic_nopin_nopassphrase()

        inp1 = proto.TxInputType(
            address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
            # amount=390000,
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
        )

        # Following address_n has been mined by 'test_mine_zero_signature'
        out1 = proto.TxOutputType(
            address_n=[177],
            amount=390000 - 10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        _, serialized_tx = btc.sign_tx(
            self.client, "Bitcoin", [inp1], [out1], prev_txes=tx_cache("Bitcoin")
        )
        siglen = serialized_tx[44]

        # TREZOR must strip leading zero from signature
        assert siglen == 67

    def test_two_zero_signature(self):
        self.setup_mnemonic_nopin_nopassphrase()

        inp1 = proto.TxInputType(
            address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
            # amount=390000,
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
        )

        # Following address_n has been mined by 'test_mine_zero_signature'
        out1 = proto.TxOutputType(
            address_n=[16518],
            amount=390000 - 10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        _, serialized_tx = btc.sign_tx(
            self.client, "Bitcoin", [inp1], [out1], prev_txes=tx_cache("Bitcoin")
        )
        siglen = serialized_tx[44]

        # TREZOR must strip leading zero from signature
        assert siglen == 66
