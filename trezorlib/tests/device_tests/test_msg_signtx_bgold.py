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

from binascii import hexlify, unhexlify

import pytest

from trezorlib import btc, coins, messages as proto
from trezorlib.tools import H_, CallException, parse_path

from ..support.ckd_public import deserialize
from .common import TrezorTest

TxApiBitcoinGold = coins.tx_api["Bgold"]


# All data taken from T1
class TestMsgSigntxBitcoinGold(TrezorTest):
    def test_send_bitcoin_gold_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBitcoinGold)
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/156'/0'/0/0"),
            amount=1995344,
            prev_hash=unhexlify(
                "25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985"
            ),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("44'/156'/0'/1/0"),
            amount=1896050,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=73452,
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
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
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
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            (signatures, serialized_tx) = btc.sign_tx(
                self.client, "Bgold", [inp1], [out1, out2]
            )

        assert (
            hexlify(serialized_tx)
            == b"010000000185c9dd4ae1071affd77d90b9d03c1b5fdd7c62cf30a9bb8230ad766cf06b5225000000006b483045022100963904da0731b71ce468afd45366dd80fbff566ec0d39c1161ab85d17459c7ca02202f5c24a7a7272d98b14a3f5bc000c7cde8ac0eb773f20f4c3131518186cc98854121023bd0ec4022d12d0106c5b7308a25572953ba1951f576f691354a7b147ee0cc1fffffffff0272ee1c00000000001976a9141c82b9c11f193ad82413caadc0955730572b50ae88acec1e0100000000001976a914ea5f904d195079a350b534db4446433b3cec222e88ac00000000"
        )

    def test_send_bitcoin_gold_nochange(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBitcoinGold)
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/156'/0'/1/0"),
            amount=1896050,
            prev_hash=unhexlify(
                "25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985"
            ),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        inp2 = proto.TxInputType(
            address_n=parse_path("44'/156'/0'/0/1"),
            # 1LRspCZNFJcbuNKQkXgHMDucctFRQya5a3
            amount=73452,
            prev_hash=unhexlify(
                "db77c2461b840e6edbe7f9280043184a98e020d9795c1b65cb7cef2551a8fb18"
            ),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=1934960,
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
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
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
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            (signatures, serialized_tx) = btc.sign_tx(
                self.client, "Bgold", [inp1, inp2], [out1]
            )

        assert (
            hexlify(serialized_tx)
            == b"010000000285c9dd4ae1071affd77d90b9d03c1b5fdd7c62cf30a9bb8230ad766cf06b5225000000006b483045022100928852076c9fab160c07564cd54691af1cbc37fb28f0b7bee7299c7925ef62f0022058856387afecc6508f2f04ecdfd292a13026a5b2107ebdd2cc789bdf8820d552412102a6c3998d0d4e5197ff41aab5c53580253b3b91f583f4c31f7624be7dc83ce15fffffffff18fba85125ef7ccb651b5c79d920e0984a18430028f9e7db6e0e841b46c277db010000006b483045022100faa2f4f01cc95e680349a093923aae0aa2ea01429873555aa8a84bf630ef33a002204c3f4bf567e2d20540c0f71dc278481d6ccb6b95acda2a2f87ce521c79d6b872412102d54a7e5733b1635e5e9442943f48179b1700206b2d1925250ba10f1c86878be8ffffffff0170861d00000000001976a914ea5f904d195079a350b534db4446433b3cec222e88ac00000000"
        )

    def test_attack_change_input(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBitcoinGold)
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/156'/1000'/0/0"),
            # 1MH9KKcvdCTY44xVDC2k3fjBbX5Cz29N1q
            amount=1995344,
            prev_hash=unhexlify(
                "25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985"
            ),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("44'/156'/1000'/1/0"),
            amount=1896050,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=73452,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        global attack_ctr
        attack_ctr = 0

        def attack_processor(req, msg):
            global attack_ctr

            if req.details.tx_hash is not None:
                return msg

            if req.request_type != proto.RequestType.TXINPUT:
                return msg

            attack_ctr += 1
            if attack_ctr <= 1:
                return msg

            msg.inputs[0].address_n[2] = H_(1)
            return msg

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
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.Failure(code=proto.FailureType.ProcessError),
                ]
            )
            with pytest.raises(CallException):
                btc.sign_tx(
                    self.client,
                    "Bgold",
                    [inp1],
                    [out1, out2],
                    debug_processor=attack_processor,
                )

    def test_send_bch_multisig_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBitcoinGold)
        xpubs = []
        for n in map(
            lambda index: btc.get_public_node(
                self.client, parse_path("44'/156'/" + str(index) + "'")
            ),
            range(1, 4),
        ):
            xpubs.append(n.xpub)

        def getmultisig(chain, nr, signatures=[b"", b"", b""], xpubs=xpubs):
            return proto.MultisigRedeemScriptType(
                pubkeys=list(
                    map(
                        lambda xpub: proto.HDNodePathType(
                            node=deserialize(xpub), address_n=[chain, nr]
                        ),
                        xpubs,
                    )
                ),
                signatures=signatures,
                m=2,
            )

        inp1 = proto.TxInputType(
            address_n=parse_path("44'/156'/3'/0/0"),
            multisig=getmultisig(0, 0),
            # 33Ju286QvonBz5N1V754ZekQv4GLJqcc5R
            amount=48490,
            prev_hash=unhexlify(
                "25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985"
            ),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDMULTISIG,
        )
        out1 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=24000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address_n=parse_path("44'/156'/3'/1/0"),
            multisig=getmultisig(1, 0),
            script_type=proto.OutputScriptType.PAYTOMULTISIG,
            amount=24000,
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
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            (signatures1, serialized_tx) = btc.sign_tx(
                self.client, "Bgold", [inp1], [out1, out2]
            )

        assert (
            hexlify(signatures1[0])
            == b"3045022100b1594f3b186d0dedbf61e53a1c407b1e0747098b7375941df85af045040f578e022013ba1893eb9e2fd854dd07073a83b261cf4beba76f66b07742e462b4088a7e4a"
        )

        inp1 = proto.TxInputType(
            address_n=parse_path("44'/156'/1'/0/0"),
            multisig=getmultisig(0, 0, [b"", b"", signatures1[0]]),
            # 33Ju286QvonBz5N1V754ZekQv4GLJqcc5R
            amount=48490,
            prev_hash=unhexlify(
                "25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985"
            ),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDMULTISIG,
        )
        out2.address_n[2] = H_(1)

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
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            (signatures1, serialized_tx) = btc.sign_tx(
                self.client, "Bgold", [inp1], [out1, out2]
            )

        assert (
            hexlify(signatures1[0])
            == b"3044022006da8dbd14e6656ac8dcb956f4c0498574e88680eaeceb2cbafd8d2b2329d8cc02200972d076d444c5ff8f2ab18e14d8249ab661cb9c53335039bedcde037a40d747"
        )
        assert (
            hexlify(serialized_tx)
            == b"010000000185c9dd4ae1071affd77d90b9d03c1b5fdd7c62cf30a9bb8230ad766cf06b522500000000fdfd0000473044022006da8dbd14e6656ac8dcb956f4c0498574e88680eaeceb2cbafd8d2b2329d8cc02200972d076d444c5ff8f2ab18e14d8249ab661cb9c53335039bedcde037a40d74741483045022100b1594f3b186d0dedbf61e53a1c407b1e0747098b7375941df85af045040f578e022013ba1893eb9e2fd854dd07073a83b261cf4beba76f66b07742e462b4088a7e4a414c69522102290e6649574d17938c1ecb959ae92954f9ee48e1bd5b73f35ea931a3ab8a6087210379e0107b173e2c143426760627128c5eea3f862e8df92f3c2558eeeae4e347842103ff1746ca7dcf9e5c2eea9a73779b7c5bafed549f45cf3638a94cdf1e89c7f28f53aeffffffff02c05d0000000000001976a914ea5f904d195079a350b534db4446433b3cec222e88acc05d00000000000017a91445e917e46815d2b38d3f1cf072e63dd4f3b7a7e38700000000"
        )

    def test_send_p2sh(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBitcoinGold)
        inp1 = proto.TxInputType(
            address_n=parse_path("49'/156'/0'/1/0"),
            amount=123456789,
            prev_hash=unhexlify(
                "25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985"
            ),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDP2SHWITNESS,
        )
        out1 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=12300000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address="GZFLExxrvWFuFT1xRzhfwQWSE2bPDedBfn",
            script_type=proto.OutputScriptType.PAYTOADDRESS,
            amount=123456789 - 11000 - 12300000,
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
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
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
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            (signatures, serialized_tx) = btc.sign_tx(
                self.client, "Bgold", [inp1], [out1, out2]
            )

        assert (
            hexlify(serialized_tx)
            == b"0100000000010185c9dd4ae1071affd77d90b9d03c1b5fdd7c62cf30a9bb8230ad766cf06b52250000000017160014b5355d001e720d8f4513da00ff2bba4dcf9d39fcffffffff02e0aebb00000000001976a914ea5f904d195079a350b534db4446433b3cec222e88ac3df39f06000000001976a914a8f757819ec6779409f45788f7b4a0e8f51ec50488ac02473044022073fcbf2876f073f78923ab427f14de5b2a0fbeb313a9b2b650b3567061f242a702202f45fc22c501108ff6222afe3aca7da9d8c7dc860f9cda335bef31fa184e7bef412102ecea08b559fc5abd009acf77cfae13fa8a3b1933e3e031956c65c12cec8ca3e300000000"
        )

    def test_send_p2sh_witness_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBitcoinGold)
        inp1 = proto.TxInputType(
            address_n=parse_path("49'/156'/0'/1/0"),
            amount=123456789,
            prev_hash=unhexlify(
                "25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985"
            ),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDP2SHWITNESS,
        )
        out1 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=12300000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address_n=parse_path("49'/156'/0'/1/0"),
            script_type=proto.OutputScriptType.PAYTOP2SHWITNESS,
            amount=123456789 - 11000 - 12300000,
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
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            (signatures, serialized_tx) = btc.sign_tx(
                self.client, "Bgold", [inp1], [out1, out2]
            )

        # print(hexlify(serialized_tx))
        # assert False
        assert (
            hexlify(serialized_tx)
            == b"0100000000010185c9dd4ae1071affd77d90b9d03c1b5fdd7c62cf30a9bb8230ad766cf06b52250000000017160014b5355d001e720d8f4513da00ff2bba4dcf9d39fcffffffff02e0aebb00000000001976a914ea5f904d195079a350b534db4446433b3cec222e88ac3df39f060000000017a9140cd03822b799a452c106d1b3771844a067b17f118702483045022100d79b33384c686d8dd40ad5f84f46691d30994992c1cb42e934c2a625d86cb2f902206859805a9a98ba140b71a9d4b9a6b8df94a9424f9c40f3bd804149fd6e278d63412102ecea08b559fc5abd009acf77cfae13fa8a3b1933e3e031956c65c12cec8ca3e300000000"
        )

    def test_send_multisig_1(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBitcoinGold)
        nodes = map(
            lambda index: btc.get_public_node(
                self.client, parse_path("999'/1'/%d'" % index)
            ),
            range(1, 4),
        )
        multisig = proto.MultisigRedeemScriptType(
            pubkeys=list(
                map(
                    lambda n: proto.HDNodePathType(
                        node=deserialize(n.xpub), address_n=[2, 0]
                    ),
                    nodes,
                )
            ),
            signatures=[b"", b"", b""],
            m=2,
        )

        inp1 = proto.TxInputType(
            address_n=parse_path("999'/1'/1'/2/0"),
            prev_hash=unhexlify(
                "25526bf06c76ad3082bba930cf627cdd5f1b3cd0b9907dd7ff1a07e14addc985"
            ),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDP2SHWITNESS,
            multisig=multisig,
            amount=1610436,
        )

        out1 = proto.TxOutputType(
            address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
            amount=1605000,
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
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            (signatures1, _) = btc.sign_tx(self.client, "Bgold", [inp1], [out1])
            # store signature
            inp1.multisig.signatures[0] = signatures1[0]
            # sign with third key
            inp1.address_n[2] = H_(3)
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
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            (signatures2, serialized_tx) = btc.sign_tx(
                self.client, "Bgold", [inp1], [out1]
            )

        assert (
            hexlify(serialized_tx)
            == b"0100000000010185c9dd4ae1071affd77d90b9d03c1b5fdd7c62cf30a9bb8230ad766cf06b522501000000232200201e8dda334f11171190b3da72e526d441491464769679a319a2f011da5ad312a1ffffffff01887d1800000000001976a914ea5f904d195079a350b534db4446433b3cec222e88ac0400483045022100e728485c8337f9a09ebbf36edc0fef10f8bcf5c1ba601b7d8ba43a9250a898f002206b9e3401c297f9ab9afb7f1be59bb342db53b5b65aff7c557e3109679697df0f41473044022062ea69ecdc07d0dadc1971fbda50a629a56dd30f431db26327428f4992601ce602204a1c8ab9c7d81c36cb6f819109a26f9baaa9607b8d37bff5e24eee6fab4a04e441695221038e81669c085a5846e68e03875113ddb339ecbb7cb11376d4163bca5dc2e2a0c1210348c5c3be9f0e6cf1954ded1c0475beccc4d26aaa9d0cce2dd902538ff1018a112103931140ebe0fbbb7df0be04ed032a54e9589e30339ba7bbb8b0b71b15df1294da53ae00000000"
        )
