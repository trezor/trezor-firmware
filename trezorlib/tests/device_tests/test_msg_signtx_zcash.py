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

import pytest

from trezorlib import btc, messages as proto
from trezorlib.tools import parse_path

from ..support.tx_cache import tx_cache
from .common import TrezorTest

TX_API = tx_cache("Zcash Testnet")

TXHASH_aaf51e = bytes.fromhex(
    "aaf51e4606c264e47e5c42c958fe4cf1539c5172684721e38e69f4ef634d75dc"
)
TXHASH_e38206 = bytes.fromhex(
    "e3820602226974b1dd87b7113cc8aea8c63e5ae29293991e7bfa80c126930368"
)


@pytest.mark.zcash
class TestMsgSigntxZcash(TrezorTest):
    def test_one_one_fee_overwinter(self):
        self.setup_mnemonic_allallall()

        # prevout: aaf51e4606c264e47e5c42c958fe4cf1539c5172684721e38e69f4ef634d75dc:1
        # input 1: 3.0 TAZ

        inp1 = proto.TxInputType(
            address_n=parse_path(
                "m/Zcash Testnet/0h/0/0"
            ),  # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
            amount=300000000,
            prev_hash=TXHASH_aaf51e,
            prev_index=1,
        )

        out1 = proto.TxOutputType(
            address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
            amount=300000000 - 1940,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )

            details = proto.SignTx(
                version=3, overwintered=True, version_group_id=0x3C48270
            )
            _, serialized_tx = btc.sign_tx(
                self.client,
                "Zcash Testnet",
                [inp1],
                [out1],
                details=details,
                prev_txes=TX_API,
            )

        # Accepted by network: tx eda9b772c47f0c29310759960e0081c98707aa67a0a2738bcc71439fcf360675
        assert (
            serialized_tx.hex()
            == "030000807082c40301dc754d63eff4698ee321476872519c53f14cfe58c9425c7ee464c206461ef5aa010000006a47304402207e45f303b4e42be824513855eb21653e1d2749cd94dcd0f0613d3f85d4efd1e20220699ffbdbcad889af7ede5ce9febf7a5ef8f5619b2464824529974c400cffaebc0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff016c9be111000000001976a9145b157a678a10021243307e4bb58f36375aa80e1088ac000000000000000000"
        )

    def test_one_one_fee_sapling(self):
        self.setup_mnemonic_allallall()

        # prevout: e3820602226974b1dd87b7113cc8aea8c63e5ae29293991e7bfa80c126930368:0
        # input 1: 3.0 TAZ

        inp1 = proto.TxInputType(
            address_n=parse_path(
                "m/Zcash Testnet/0h/0/0"
            ),  # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
            amount=300000000,
            prev_hash=TXHASH_e38206,
            prev_index=0,
        )

        out1 = proto.TxOutputType(
            address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
            amount=300000000 - 1940,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )

            details = proto.SignTx(
                version=4, overwintered=True, version_group_id=0x892F2085
            )
            _, serialized_tx = btc.sign_tx(
                self.client,
                "Zcash Testnet",
                [inp1],
                [out1],
                details=details,
                prev_txes=TX_API,
            )

        # Accepted by network: tx 0cef132c1d6d67f11cfa48f7fca3209da29cf872ac782354bedb686e61a17a78
        assert (
            serialized_tx.hex()
            == "0400008085202f890168039326c180fa7b1e999392e25a3ec6a8aec83c11b787ddb1746922020682e3000000006b483045022100f28298891f48706697a6f898ac18e39ce2c7cebe547b585d51cc22d80b1b21a602201a807b8a18544832d95d1e3ada82c0617bc6d97d3f24d1fb4801ac396647aa880121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff016c9be111000000001976a9145b157a678a10021243307e4bb58f36375aa80e1088ac00000000000000000000000000000000000000"
        )
