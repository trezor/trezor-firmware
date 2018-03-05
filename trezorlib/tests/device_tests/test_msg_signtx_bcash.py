# This file is part of the TREZOR project.
#
# Copyright (C) 2017 Jochen Hoenicke <hoenicke@gmail.com>
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
from trezorlib.tx_api import TxApiBcash
from trezorlib.ckd_public import deserialize
from trezorlib.client import CallException


class TestMsgSigntxBch(TrezorTest):

    def test_send_bch_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBcash)
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/145'/0'/0/0"),
            # 1MH9KKcvdCTY44xVDC2k3fjBbX5Cz29N1q
            amount=1995344,
            prev_hash=unhexlify('bc37c28dfb467d2ecb50261387bf752a3977d7e5337915071bb4151e6b711a78'),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=self.client.expand_path("44'/145'/0'/1/0"),
            amount=1896050,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address='1LRspCZNFJcbuNKQkXgHMDucctFRQya5a3',
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
            (signatures, serialized_tx) = self.client.sign_tx('Bcash', [inp1], [out1, out2])

        assert hexlify(serialized_tx) == b'0100000001781a716b1e15b41b07157933e5d777392a75bf87132650cb2e7d46fb8dc237bc000000006a473044022061aee4f17abe044d5df8c52c9ffd3b84e5a29743517e488b20ecf1ae0b3e4d3a02206bb84c55e407f3b684ff8d9bea0a3409cfd865795a19d10b3d3c31f12795c34a412103a020b36130021a0f037c1d1a02042e325c0cb666d6478c1afdcd9d913b9ef080ffffffff0272ee1c00000000001976a914b1401fce7e8bf123c88a0467e0ed11e3b9fbef5488acec1e0100000000001976a914d51eca49695cdf47e7f4b55507893e3ad53fe9d888ac00000000'

    def test_send_bch_nochange(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBcash)
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/145'/0'/1/0"),
            # 1HADRPJpgqBzThepERpVXNi6qRgiLQRNoE
            amount=1896050,
            prev_hash=unhexlify('502e8577b237b0152843a416f8f1ab0c63321b1be7a8cad7bf5c5c216fcf062c'),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        inp2 = proto.TxInputType(
            address_n=self.client.expand_path("44'/145'/0'/0/1"),
            # 1LRspCZNFJcbuNKQkXgHMDucctFRQya5a3
            amount=73452,
            prev_hash=unhexlify('502e8577b237b0152843a416f8f1ab0c63321b1be7a8cad7bf5c5c216fcf062c'),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address='15pnEDZJo3ycPUamqP3tEDnEju1oW5fBCz',
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
            (signatures, serialized_tx) = self.client.sign_tx('Bcash', [inp1, inp2], [out1])

        assert hexlify(serialized_tx) == b'01000000022c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50000000006a47304402207a2a955f1cb3dc5f03f2c82934f55654882af4e852e5159639f6349e9386ec4002205fb8419dce4e648eae8f67bc4e369adfb130a87d2ea2d668f8144213b12bb457412103174c61e9c5362507e8061e28d2c0ce3d4df4e73f3535ae0b12f37809e0f92d2dffffffff2c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50010000006a473044022062151cf960b71823bbe68c7ed2c2a93ad1b9706a30255fddb02fcbe056d8c26102207bad1f0872bc5f0cfaf22e45c925c35d6c1466e303163b75cb7688038f1a5541412102595caf9aeb6ffdd0e82b150739a83297358b9a77564de382671056ad9e5b8c58ffffffff0170861d00000000001976a91434e9cec317896e818619ab7dc99d2305216ff4af88ac00000000'

    def test_attack_amount(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBcash)
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/145'/0'/1/0"),
            # 1HADRPJpgqBzThepERpVXNi6qRgiLQRNoE
            amount=300,
            prev_hash=unhexlify('502e8577b237b0152843a416f8f1ab0c63321b1be7a8cad7bf5c5c216fcf062c'),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        inp2 = proto.TxInputType(
            address_n=self.client.expand_path("44'/145'/0'/0/1"),
            # 1LRspCZNFJcbuNKQkXgHMDucctFRQya5a3
            amount=70,
            prev_hash=unhexlify('502e8577b237b0152843a416f8f1ab0c63321b1be7a8cad7bf5c5c216fcf062c'),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address='15pnEDZJo3ycPUamqP3tEDnEju1oW5fBCz',
            amount=200,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        global run_attack
        run_attack = True

        def attack_processor(req, msg):
            global run_attack

            if req.details.tx_hash is not None:
                return msg

            if req.request_type != proto.RequestType.TXINPUT:
                return msg

            if req.details.request_index != 0:
                return msg

            if not run_attack:
                return msg

            # 300 is lowered to 280 at the first run
            # the user confirms 280 but the transaction
            # is spending 300 => larger fee without the user knowing
            msg.inputs[0].amount = 280
            run_attack = False
            return msg

        # test if passes without modifications
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
            self.client.sign_tx('Bcash', [inp1, inp2], [out1])

        # now fails
        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.Failure(code=proto.FailureType.ProcessError),
            ])

            try:
                self.client.sign_tx('Bcash', [inp1, inp2], [out1], debug_processor=attack_processor)
            except CallException as exc:
                assert exc.args[0] == proto.FailureType.ProcessError
                assert exc.args[1] == 'Transaction has changed during signing'
            else:
                assert False  # exception expected

    def test_attack_change_input(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBcash)
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/145'/1000'/0/0"),
            # 1MH9KKcvdCTY44xVDC2k3fjBbX5Cz29N1q
            amount=1995344,
            prev_hash=unhexlify('bc37c28dfb467d2ecb50261387bf752a3977d7e5337915071bb4151e6b711a78'),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=self.client.expand_path("44'/145'/1000'/1/0"),
            amount=1896050,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address='1LRspCZNFJcbuNKQkXgHMDucctFRQya5a3',
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
                self.client.sign_tx('Bcash', [inp1], [out1, out2], debug_processor=attack_processor)

    def test_send_bch_multisig_wrongchange(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBcash)
        xpubs = []
        for n in map(lambda index: self.client.get_public_node(self.client.expand_path("44'/145'/" + str(index) + "'")), range(1, 4)):
            xpubs.append(n.xpub)

        def getmultisig(chain, nr, signatures=[b'', b'', b''], xpubs=xpubs):
            return proto.MultisigRedeemScriptType(
                pubkeys=list(map(lambda xpub: proto.HDNodePathType(node=deserialize(xpub), address_n=[chain, nr]), xpubs)),
                signatures=signatures,
                m=2,
            )
        correcthorse = proto.HDNodeType(
            depth=1, fingerprint=0, child_num=0,
            chain_code=unhexlify('0000000000000000000000000000000000000000000000000000000000000000'),
            public_key=unhexlify('0378d430274f8c5ec1321338151e9f27f4c676a008bdf8638d07c0b6be9ab35c71'))
        sig = unhexlify(b'304402207274b5a4d15e75f3df7319a375557b0efba9b27bc63f9f183a17da95a6125c94022000efac57629f1522e2d3958430e2ef073b0706cfac06cce492651b79858f09ae')
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/145'/1'/1/0"),
            multisig=getmultisig(1, 0, [b'', sig, b'']),
            # 3CPtPpL5mGAPdxUeUDfm2RNdWoSN9dKpXE
            amount=24000,
            prev_hash=unhexlify('f68caf10df12d5b07a34601d88fa6856c6edcbf4d05ebef3486510ae1c293d5f'),
            prev_index=1,
            script_type=proto.InputScriptType.SPENDMULTISIG,
        )
        out1 = proto.TxOutputType(
            address_n=self.client.expand_path("44'/145'/1'/1/1"),
            multisig=proto.MultisigRedeemScriptType(
                pubkeys=[proto.HDNodePathType(node=deserialize(xpubs[0]), address_n=[1, 1]),
                         proto.HDNodePathType(node=correcthorse, address_n=[]),
                         proto.HDNodePathType(node=correcthorse, address_n=[])],
                signatures=[b'', b'', b''],
                m=2,
            ),
            script_type=proto.OutputScriptType.PAYTOMULTISIG,
            amount=23000
        )
        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures1, serialized_tx) = self.client.sign_tx('Bcash', [inp1], [out1])
        assert hexlify(signatures1[0]) == b'3044022052ccf022b3684ecce9f961ce8828387b97267c86bedf0ce16a24bf014e62e42c022035d315ddbeeef7ab3456bd09aed8b625ea58852216b60e4b84ba9f85827d305c'
        assert hexlify(serialized_tx) == b'01000000015f3d291cae106548f3be5ed0f4cbedc65668fa881d60347ab0d512df10af8cf601000000fc00473044022052ccf022b3684ecce9f961ce8828387b97267c86bedf0ce16a24bf014e62e42c022035d315ddbeeef7ab3456bd09aed8b625ea58852216b60e4b84ba9f85827d305c4147304402207274b5a4d15e75f3df7319a375557b0efba9b27bc63f9f183a17da95a6125c94022000efac57629f1522e2d3958430e2ef073b0706cfac06cce492651b79858f09ae414c69522103d62b2af2272bbd67cbe30eeaf4226c7f2d57d2a0ed1aab5ab736fb40bb2f5ffe21036d5e0d7ca3589465711eec91436249d7234d3a994c219024fc75cec98fc02ae221024f58378a69b68e89301a6ff882116e0fa35446ec9bfd86532eeb05941ec1f8c853aeffffffff01d85900000000000017a9140bb11de6558871f49fc241341992ece9986f7c5c8700000000'

    def test_send_bch_multisig_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiBcash)
        xpubs = []
        for n in map(lambda index: self.client.get_public_node(self.client.expand_path("44'/145'/" + str(index) + "'")), range(1, 4)):
            xpubs.append(n.xpub)

        def getmultisig(chain, nr, signatures=[b'', b'', b''], xpubs=xpubs):
            return proto.MultisigRedeemScriptType(
                pubkeys=list(map(lambda xpub: proto.HDNodePathType(node=deserialize(xpub), address_n=[chain, nr]), xpubs)),
                signatures=signatures,
                m=2,
            )
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/145'/3'/0/0"),
            multisig=getmultisig(0, 0),
            # 33Ju286QvonBz5N1V754ZekQv4GLJqcc5R
            amount=48490,
            prev_hash=unhexlify('8b6db9b8ba24235d86b053ea2ccb484fc32b96f89c3c39f98d86f90db16076a0'),
            prev_index=0,
            script_type=proto.InputScriptType.SPENDMULTISIG,
        )
        out1 = proto.TxOutputType(
            address='113Q5hHQNQ3bc1RpPX6UNw4GAXstyeA3Dk',
            amount=24000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address_n=self.client.expand_path("44'/145'/3'/1/0"),
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
            (signatures1, serialized_tx) = self.client.sign_tx('Bcash', [inp1], [out1, out2])

        assert hexlify(signatures1[0]) == b'3045022100bcb1a7134a13025a06052546ee1c6ac3640a0abd2d130190ed13ed7fcb43e9cd02207c381478e2ee123c850425bfbf6d3c691230eb37e333832cb32a1ed3f2cd9e85'

        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/145'/1'/0/0"),
            multisig=getmultisig(0, 0, [b'', b'', signatures1[0]]),
            # 33Ju286QvonBz5N1V754ZekQv4GLJqcc5R
            amount=48490,
            prev_hash=unhexlify('8b6db9b8ba24235d86b053ea2ccb484fc32b96f89c3c39f98d86f90db16076a0'),
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
            (signatures1, serialized_tx) = self.client.sign_tx('Bcash', [inp1], [out1, out2])

        assert hexlify(signatures1[0]) == b'3045022100f1153636371ba1f84389460e1265a8fa296569bc18e117c31f4e8f0fc0650c01022022932cc84766ff0c0f65ed9633ad311ae90d4c8fe71f5e1890b1e8f74dd516fa'
        assert hexlify(serialized_tx) == b'0100000001a07660b10df9868df9393c9cf8962bc34f48cb2cea53b0865d2324bab8b96d8b00000000fdfe0000483045022100f1153636371ba1f84389460e1265a8fa296569bc18e117c31f4e8f0fc0650c01022022932cc84766ff0c0f65ed9633ad311ae90d4c8fe71f5e1890b1e8f74dd516fa41483045022100bcb1a7134a13025a06052546ee1c6ac3640a0abd2d130190ed13ed7fcb43e9cd02207c381478e2ee123c850425bfbf6d3c691230eb37e333832cb32a1ed3f2cd9e85414c69522102fcf63419c319ce1a42d69120a3599d6da8c5dd4caf2888220eccde5a1ff7c5d021036d7d5ef79370b7fabe2c058698a20219e97fc70868e65ecdd6b37cc18e8a88bd2103505dc649dab8cd1655a4c0daf0ec5f955881c9d7011478ea881fac11cab1e49953aeffffffff02c05d0000000000001976a91400741952f6a6eab5394f366db5cc5a54b0c2429f88acc05d00000000000017a914756c06d7e77de3950a6124f026d8e1a2464b3ecf8700000000'
