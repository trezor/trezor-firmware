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

import unittest
import common
import binascii

import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types
from trezorlib.tx_api import TxApiTestnet
from trezorlib.ckd_public import deserialize
from trezorlib.client import CallException


class TestMsgSigntxSegwit(common.TrezorTest):

    def test_send_bcc_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        inp1 = proto_types.TxInputType(
            address_n=self.client.expand_path("44'/1'/4'/0/0"),
            # moUJnmge8SRXuediK7bW6t4YfrPqbE6hD7
            amount=123400000,
            prev_hash=binascii.unhexlify('d2dcdaf547ea7f57a713c607f15e883ddc4a98167ee2c43ed953c53cb5153e24'),
            prev_index=1,
            script_type=proto_types.SPENDADDRESS,
        )
        inp2 = proto_types.TxInputType(
            address_n=self.client.expand_path("44'/1'/4'/0/1"),
            # mhSeXqbaojGkaezxgwobgMxGHzv79x7rhK
            amount=43210000,
            prev_hash=binascii.unhexlify('fe26bc077de27b72ffc5ce77a7e296c7c855b7deb3dec72a3f82c0c07c722bb0'),
            prev_index=1,
            script_type=proto_types.SPENDADDRESS,
        )
        out1 = proto_types.TxOutputType(
            address='mwue7mokpBRAsJtHqEMcRPanYBmsSmYKvY',
            amount=100000000,
            script_type=proto_types.PAYTOADDRESS,
        )
        out2 = proto_types.TxOutputType(
            address_n=self.client.expand_path("44'/1'/4'/1/0"),
            script_type=proto_types.PAYTOADDRESS,
            amount=23400000 + 43210000 - 5000
        )
        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Testnet Cash', [inp1, inp2], [out1, out2])

        print(binascii.hexlify(serialized_tx))
        self.assertEqual(binascii.hexlify(serialized_tx), b'0100000002243e15b53cc553d93ec4e27e16984adc3d885ef107c613a7577fea47f5dadcd2010000006b483045022100ebcce894cac5d1750f4b1abc7d8c0a5d25944c12a02942b0cc1c89c397acc09602207335077bd698cefc1694d5817abdb3b7aecfcd110ca07729d893577ada71d35441210364430c9122948e525e2f1c6d88f00f47679274f0810fd8c63754954f310995c1ffffffffb02b727cc0c0823f2ac7deb3deb755c8c796e2a777cec5ff727be27d07bc26fe010000006b4830450221008a140434b3f105686c6c4a704c9f2d09b2faf633b81b9ec2304b81f2fd617a9c0220497279b656c4034fd30c41c6f1d0e2ad2aa1b867575aa8f4c13218cb8c114140412103749e3f0a7b01f73427ed67c1cedbb4ecd2315ad6b7c2513355393b95d1ba6137ffffffff0200e1f505000000001976a914b3cc67f3349974d0f1b50e9bb5dfdf226f888fa088acc84ff803000000001976a914f80fb232a1e54b1fa732bc120cae72eabd7fcf6888ac00000000')

    def test_attack_amount(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        inp1 = proto_types.TxInputType(
            address_n=self.client.expand_path("44'/1'/4'/0/0"),
            # moUJnmge8SRXuediK7bW6t4YfrPqbE6hD7
            amount=123399999,
            prev_hash=binascii.unhexlify('d2dcdaf547ea7f57a713c607f15e883ddc4a98167ee2c43ed953c53cb5153e24'),
            prev_index=1,
            script_type=proto_types.SPENDADDRESS,
        )
        inp2 = proto_types.TxInputType(
            address_n=self.client.expand_path("44'/1'/4'/0/1"),
            # mhSeXqbaojGkaezxgwobgMxGHzv79x7rhK
            amount=43210000,
            prev_hash=binascii.unhexlify('fe26bc077de27b72ffc5ce77a7e296c7c855b7deb3dec72a3f82c0c07c722bb0'),
            prev_index=1,
            script_type=proto_types.SPENDADDRESS,
        )
        out1 = proto_types.TxOutputType(
            address='mwue7mokpBRAsJtHqEMcRPanYBmsSmYKvY',
            amount=100000000,
            script_type=proto_types.PAYTOADDRESS,
        )
        out2 = proto_types.TxOutputType(
            address_n=self.client.expand_path("44'/1'/4'/1/0"),
            script_type=proto_types.PAYTOADDRESS,
            amount=23399999 + 43210000 - 5000
        )

        global run_attack
        run_attack = True

        def attack_processor(req, msg):
            import sys
            global run_attack

            if req.details.tx_hash != b'':
                return msg

            if req.request_type != proto_types.TXINPUT:
                return msg

            if req.details.request_index != 0:
                return msg

            if not run_attack:
                return msg

            msg.inputs[0].amount = 123400000
            run_attack = False
            return msg

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.Failure(code=proto_types.Failure_ProcessError),
            ])
            self.assertRaises(CallException, self.client.sign_tx, 'Testnet Cash', [inp1, inp2], [out1, out2], debug_processor=attack_processor)

    def test_attack_change_input(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)
        inp1 = proto_types.TxInputType(
            address_n=self.client.expand_path("44'/1'/4'/0/0"),
            # moUJnmge8SRXuediK7bW6t4YfrPqbE6hD7
            amount=123400000,
            prev_hash=binascii.unhexlify('d2dcdaf547ea7f57a713c607f15e883ddc4a98167ee2c43ed953c53cb5153e24'),
            prev_index=1,
            script_type=proto_types.SPENDADDRESS,
        )
        inp2 = proto_types.TxInputType(
            address_n=self.client.expand_path("44'/1'/4'/0/1"),
            # mhSeXqbaojGkaezxgwobgMxGHzv79x7rhK
            amount=43210000,
            prev_hash=binascii.unhexlify('fe26bc077de27b72ffc5ce77a7e296c7c855b7deb3dec72a3f82c0c07c722bb0'),
            prev_index=1,
            script_type=proto_types.SPENDADDRESS,
        )
        out1 = proto_types.TxOutputType(
            address='mwue7mokpBRAsJtHqEMcRPanYBmsSmYKvY',
            amount=100000000,
            script_type=proto_types.PAYTOADDRESS,
        )
        out2 = proto_types.TxOutputType(
            address_n=self.client.expand_path("44'/1'/1'/1/0"),
            script_type=proto_types.PAYTOADDRESS,
            amount=23400000 + 43210000 - 5000
        )

        global attack_ctr
        attack_ctr = 0

        def attack_processor(req, msg):
            import sys
            global attack_ctr

            if req.details.tx_hash != b'':
                return msg

            if req.request_type != proto_types.TXINPUT:
                return msg

            attack_ctr += 1
            if attack_ctr > 2:
                return msg

            msg.inputs[0].address_n[2] = 1 + 0x80000000
            return msg

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_ConfirmOutput),
                proto.TxRequest(request_type=proto_types.TXOUTPUT, details=proto_types.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto_types.ButtonRequest_SignTx),
                proto.TxRequest(request_type=proto_types.TXINPUT, details=proto_types.TxRequestDetailsType(request_index=0)),
                proto.Failure(code=proto_types.Failure_ProcessError),
            ])
            self.assertRaises(CallException, self.client.sign_tx, 'Testnet Cash', [inp1, inp2], [out1, out2], debug_processor=attack_processor)
