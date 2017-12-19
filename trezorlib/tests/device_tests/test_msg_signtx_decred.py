# This file is part of the TREZOR project.
#
# Copyright (C) 2017 Saleem Rashid <trezor@saleemrashid.com>
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

from . import common
import binascii
import pytest

from trezorlib import messages as proto
from trezorlib.tx_api import TxApiDecredTestnet


TXHASH_e16248 = binascii.unhexlify("e16248f0b39a0a0c0e53d6f2f84c2a944f0d50e017a82701e8e02e46e979d5ed")


@pytest.mark.skip_t1
@pytest.mark.skip_t2
class TestMsgSigntxDecred(common.TrezorTest):

    def test_send_decred(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiDecredTestnet)

        inp1 = proto.TxInputType(
            # TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz
            address_n=self.client.expand_path("m/44'/1'/0'/0/0"),
            prev_hash=TXHASH_e16248,
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
            decred_tree=0,
        )

        out1 = proto.TxOutputType(
            address="TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz",
            amount=190000000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
            decred_script_version=0,
        )

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_e16248)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_e16248, request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_e16248, request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_e16248, request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.FeeOverThreshold),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx("Decred Testnet", [inp1], [out1])

        # Accepted by network: 5e6e3500a333c53c02f523db5f1a9b17538a8850b4c2c24ecb9b7ba48059b970
        self.assertEqual(serialized_tx, binascii.unhexlify("0100000001edd579e9462ee0e80127a817e0500d4f942a4cf8f2d6530e0c0a9ab3f04862e10100000000ffffffff01802b530b0000000000001976a914819d291a2f7fbf770e784bfd78b5ce92c58e95ea88ac000000000000000001000000000000000000000000ffffffff6b483045022100bad68486491e449a731513805c129201d7f65601d6f07c97fda0588453c97d22022013e9ef59657ae4f344ac4f0db2b7a23dbfcdb51ebeb85277146ac189e547d3f7012102f5a745afb96077c071e4d19911a5d3d024faa1314ee8688bc6eec39751d0818f"))
