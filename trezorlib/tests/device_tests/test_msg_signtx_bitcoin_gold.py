# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
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

from .common import *
from trezorlib import messages as proto
from trezorlib.tx_api import TxApiBitcoinGold
from trezorlib.ckd_public import deserialize
from trezorlib.client import CallException


# All data taken from T1
class TestMsgSigntxBitcoinGold(TrezorTest):

    def test_send_bitcoin_gold_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBitcoinGold)
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/156'/0'/0/0"),
            amount=1995344,
            prev_hash=unhexlify('25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985'),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=self.client.expand_path("44'/156'/0'/1/0"),
            amount=1896050,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address='GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe',
            amount=73452,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Bitcoin Gold', [inp1], [out1, out2])

        assert hexlify(serialized_tx) == b'010000000185c9dd4ae1071affd77d90b9d03c1b5fdd7c62cf30a9bb8230ad766cf06b5225000000006b483045022100963904da0731b71ce468afd45366dd80fbff566ec0d39c1161ab85d17459c7ca02202f5c24a7a7272d98b14a3f5bc000c7cde8ac0eb773f20f4c3131518186cc98854121023bd0ec4022d12d0106c5b7308a25572953ba1951f576f691354a7b147ee0cc1fffffffff0272ee1c00000000001976a9141c82b9c11f193ad82413caadc0955730572b50ae88acec1e0100000000001976a914ea5f904d195079a350b534db4446433b3cec222e88ac00000000'

    def test_send_bitcoin_gold_nochange(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBitcoinGold)
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/156'/0'/1/0"),
            amount=1896050,
            prev_hash=unhexlify('25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985'),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        inp2 = proto.TxInputType(
            address_n=self.client.expand_path("44'/156'/0'/0/1"),
            # 1LRspCZNFJcbuNKQkXgHMDucctFRQya5a3
            amount=73452,
            prev_hash=unhexlify('db77c2461b840e6edbe7f9280043184a98e020d9795c1b65cb7cef2551a8fb18'),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address='GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe',
            amount=1934960,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Bitcoin Gold', [inp1, inp2], [out1])

        assert hexlify(serialized_tx) == b'010000000285c9dd4ae1071affd77d90b9d03c1b5fdd7c62cf30a9bb8230ad766cf06b5225000000006b483045022100928852076c9fab160c07564cd54691af1cbc37fb28f0b7bee7299c7925ef62f0022058856387afecc6508f2f04ecdfd292a13026a5b2107ebdd2cc789bdf8820d552412102a6c3998d0d4e5197ff41aab5c53580253b3b91f583f4c31f7624be7dc83ce15fffffffff18fba85125ef7ccb651b5c79d920e0984a18430028f9e7db6e0e841b46c277db010000006b483045022100faa2f4f01cc95e680349a093923aae0aa2ea01429873555aa8a84bf630ef33a002204c3f4bf567e2d20540c0f71dc278481d6ccb6b95acda2a2f87ce521c79d6b872412102d54a7e5733b1635e5e9442943f48179b1700206b2d1925250ba10f1c86878be8ffffffff0170861d00000000001976a914ea5f904d195079a350b534db4446433b3cec222e88ac00000000'

    def test_attack_change_input(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBitcoinGold)
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/156'/1000'/0/0"),
            # 1MH9KKcvdCTY44xVDC2k3fjBbX5Cz29N1q
            amount=1995344,
            prev_hash=unhexlify('25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985'),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=self.client.expand_path("44'/156'/1000'/1/0"),
            amount=1896050,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address='GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe',
            amount=73452,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        global attack_ctr
        attack_ctr = 0

        def attack_processor(req, msg):
            import sys
            global attack_ctr

            if req.details.tx_hash is not None:
                return msg

            if req.request_type != proto.RequestType.TXINPUT:
                return msg

            attack_ctr += 1
            if attack_ctr <= 1:
                return msg

            msg.inputs[0].address_n[2] = 1 + 0x80000000
            return msg

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.Failure(code=proto.FailureType.ProcessError),
            ])
            with pytest.raises(CallException):
                self.client.sign_tx('Bitcoin Gold', [inp1], [out1, out2], debug_processor=attack_processor)

    def test_send_bch_multisig_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBitcoinGold)
        xpubs = []
        for n in map(lambda index: self.client.get_public_node(self.client.expand_path("44'/156'/" + str(index) + "'")), range(1, 4)):
            xpubs.append(n.xpub)

        def getmultisig(chain, nr, signatures=[b'', b'', b''], xpubs=xpubs):
            return proto.MultisigRedeemScriptType(
                pubkeys=list(map(lambda xpub: proto.HDNodePathType(node=deserialize(xpub), address_n=[chain, nr]), xpubs)),
                signatures=signatures,
                m=2,
            )
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/156'/3'/0/0"),
            multisig=getmultisig(0, 0),
            # 33Ju286QvonBz5N1V754ZekQv4GLJqcc5R
            amount=48490,
            prev_hash=unhexlify('25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985'),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDMULTISIG,
        )
        out1 = proto.TxOutputType(
            address='GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe',
            amount=24000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address_n=self.client.expand_path("44'/156'/3'/1/0"),
            multisig=getmultisig(1, 0),
            script_type=proto.OutputScriptType.PAYTOMULTISIG,
            amount=24000
        )
        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures1, serialized_tx) = self.client.sign_tx('Bitcoin Gold', [inp1], [out1, out2])

        assert hexlify(signatures1[0]) == b'3045022100b1594f3b186d0dedbf61e53a1c407b1e0747098b7375941df85af045040f578e022013ba1893eb9e2fd854dd07073a83b261cf4beba76f66b07742e462b4088a7e4a'

        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/156'/1'/0/0"),
            multisig=getmultisig(0, 0, [b'', b'', signatures1[0]]),
            # 33Ju286QvonBz5N1V754ZekQv4GLJqcc5R
            amount=48490,
            prev_hash=unhexlify('25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985'),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDMULTISIG,
        )
        out2.address_n[2] = 1 + 0x80000000

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures1, serialized_tx) = self.client.sign_tx('Bitcoin Gold', [inp1], [out1, out2])

        assert hexlify(signatures1[0]) == b'3044022006da8dbd14e6656ac8dcb956f4c0498574e88680eaeceb2cbafd8d2b2329d8cc02200972d076d444c5ff8f2ab18e14d8249ab661cb9c53335039bedcde037a40d747'
        assert hexlify(serialized_tx) == b'010000000185c9dd4ae1071affd77d90b9d03c1b5fdd7c62cf30a9bb8230ad766cf06b522500000000fdfd0000473044022006da8dbd14e6656ac8dcb956f4c0498574e88680eaeceb2cbafd8d2b2329d8cc02200972d076d444c5ff8f2ab18e14d8249ab661cb9c53335039bedcde037a40d74741483045022100b1594f3b186d0dedbf61e53a1c407b1e0747098b7375941df85af045040f578e022013ba1893eb9e2fd854dd07073a83b261cf4beba76f66b07742e462b4088a7e4a414c69522102290e6649574d17938c1ecb959ae92954f9ee48e1bd5b73f35ea931a3ab8a6087210379e0107b173e2c143426760627128c5eea3f862e8df92f3c2558eeeae4e347842103ff1746ca7dcf9e5c2eea9a73779b7c5bafed549f45cf3638a94cdf1e89c7f28f53aeffffffff02c05d0000000000001976a914ea5f904d195079a350b534db4446433b3cec222e88acc05d00000000000017a91445e917e46815d2b38d3f1cf072e63dd4f3b7a7e38700000000'
