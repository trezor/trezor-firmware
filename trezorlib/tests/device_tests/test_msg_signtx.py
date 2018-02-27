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
from trezorlib.client import CallException
from trezorlib.tx_api import TxApiTestnet


TXHASH_157041 = unhexlify('1570416eb4302cf52979afd5e6909e37d8fdd874301f7cc87e547e509cb1caa6')
TXHASH_39a29e = unhexlify('39a29e954977662ab3879c66fb251ef753e0912223a83d1dcb009111d28265e5')
TXHASH_4a7b7e = unhexlify('4a7b7e0403ae5607e473949cfa03f09f2cd8b0f404bf99ce10b7303d86280bf7')
TXHASH_54aa56 = unhexlify('54aa5680dea781f45ebb536e53dffc526d68c0eb5c00547e323b2c32382dfba3')
TXHASH_58497a = unhexlify('58497a7757224d1ff1941488d23087071103e5bf855f4c1c44e5c8d9d82ca46e')
TXHASH_6f90f3 = unhexlify('6f90f3c7cbec2258b0971056ef3fe34128dbde30daa9c0639a898f9977299d54')
TXHASH_c63e24 = unhexlify('c63e24ed820c5851b60c54613fbc4bcb37df6cd49b4c96143e99580a472f79fb')
TXHASH_c6be22 = unhexlify('c6be22d34946593bcad1d2b013e12f74159e69574ffea21581dad115572e031c')
TXHASH_d5f65e = unhexlify('d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882')
TXHASH_d6da21 = unhexlify('d6da21677d7cca5f42fbc7631d062c9ae918a0254f7c6c22de8e8cb7fd5b8236')
TXHASH_d2dcda = unhexlify('d2dcdaf547ea7f57a713c607f15e883ddc4a98167ee2c43ed953c53cb5153e24')
TXHASH_e5040e = unhexlify('e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd')
TXHASH_50f6f1 = unhexlify('50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d')


class TestMsgSigntx(TrezorTest):
    def test_one_one_fee(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC

        inp1 = proto.TxInputType(
            address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
            # amount=390000,
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
        )

        out1 = proto.TxOutputType(
            address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
            amount=390000 - 10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])

            (signatures, serialized_tx) = self.client.sign_tx('Bitcoin', [inp1, ], [out1, ])

        # Accepted by network: tx fd79435246dee76b2f159d2db08032d666c95adc544de64c8c49f474df4a7fee
        assert hexlify(serialized_tx) == b'010000000182488650ef25a58fef6788bd71b8212038d7f2bbe4750bc7bcb44701e85ef6d5000000006b4830450221009a0b7be0d4ed3146ee262b42202841834698bb3ee39c24e7437df208b8b7077102202b79ab1e7736219387dffe8d615bbdba87e11477104b867ef47afed1a5ede7810121023230848585885f63803a0a8aecdd6538792d5c539215c91698e315bf0253b43dffffffff0160cc0500000000001976a914de9b2a8da088824e8fe51debea566617d851537888ac00000000'

    def test_testnet_one_two_fee(self):
        self.setup_mnemonic_allallall()
        # see 87be0736f202f7c2bff0781b42bad3e0cdcb54761939da69ea793a3735552c56

        # tx: e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd
        # input 0: 0.31 BTC
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/1'/0'/0/0"),
            # amount=31000000,
            prev_hash=TXHASH_e5040e,
            prev_index=0,
        )

        out1 = proto.TxOutputType(
            address='msj42CCGruhRsFrGATiUuh25dtxYtnpbTx',
            amount=30090000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        out2 = proto.TxOutputType(
            address_n=self.client.expand_path("44'/1'/0'/1/0"),
            amount=900000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_tx_api(TxApiTestnet)
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_e5040e)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_e5040e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_e5040e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_e5040e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Testnet', [inp1, ], [out1, out2])

        assert hexlify(serialized_tx) == b'0100000001cd3b93f5b24ae190ce5141235091cd93fbb2908e24e5b9ff6776aec11b0e04e5000000006b483045022100eba3bbcbb82ab1ebac88a394e8fb53b0263dadbb3e8072f0a21ee62818c911060220686a9b7f306d028b54a228b5c47cc6c27b1d01a3b0770440bcc64d55d8bace2c0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff021023cb01000000001976a91485eb47fe98f349065d6f044e27a4ac541af79ee288aca0bb0d00000000001976a9143d3cca567e00a04819742b21a696a67da796498b88ac00000000'

    def test_testnet_fee_too_high(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # tx: 6f90f3c7cbec2258b0971056ef3fe34128dbde30daa9c0639a898f9977299d54
        # input 1: 10.00000000 BTC
        inp1 = proto.TxInputType(
            address_n=[0],  # mirio8q3gtv7fhdnmb3TpZ4EuafdzSs7zL
            # amount=1000000000,
            prev_hash=TXHASH_6f90f3,
            prev_index=1,
        )

        out1 = proto.TxOutputType(
            address='mfiGQVPcRcaEvQPYDErR34DcCovtxYvUUV',
            amount=1000000000 - 500000000 - 100000000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        out2 = proto.TxOutputType(
            address_n=[2],
            amount=500000000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_tx_api(TxApiTestnet)
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_6f90f3)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_6f90f3)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_6f90f3)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_6f90f3)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_6f90f3)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.FeeOverThreshold),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Testnet', [inp1, ], [out1, out2])

        assert hexlify(serialized_tx) == b'0100000001549d2977998f899a63c0a9da30dedb2841e33fef561097b05822eccbc7f3906f010000006a47304402205ea68e9d52d4be14420ccecf7f2e11489d49b86bedb79ee99b5e9b7188884150022056219cb3384a5df8048cca286a9533403dbda1571afd84b51379cdaee6a6dea80121023230848585885f63803a0a8aecdd6538792d5c539215c91698e315bf0253b43dffffffff020084d717000000001976a9140223b1a09138753c9cb0baf95a0a62c82711567a88ac0065cd1d000000001976a9142db345c36563122e2fd0f5485fb7ea9bbf7cb5a288ac00000000'

    def test_one_two_fee(self):
        self.setup_mnemonic_allallall()

        # tx: c275c333fd1b36bef4af316226c66a8b3693fbfcc081a5e16a2ae5fcb09e92bf

        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("m/44'/0'/0'/0/5"),  # 1GA9u9TfCG7SWmKCveBumdA1TZpfom6ZdJ
            # amount=50000,
            prev_hash=TXHASH_50f6f1,
            prev_index=1,
        )

        out1 = proto.TxOutputType(
            address_n=self.client.expand_path("m/44'/0'/0'/1/3"),  # 1EcL6AyfQTyWKGvXwNSfsWoYnD3whzVFdu
            amount=30000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        out2 = proto.TxOutputType(
            address='1Up15Msx4sbvUCGm8Xgo2Zp5FQim3wE59',
            amount=10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_50f6f1)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_50f6f1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_50f6f1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_50f6f1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Bitcoin', [inp1, ], [out1, out2])

        assert hexlify(serialized_tx) == b'01000000016d20f69067ad1ffd50ee7c0f377dde2c932ccb03e84b5659732da99c20f1f650010000006a47304402203429bd3ce7b38c5c1e8a15340edd79ced41a2939aae62e259d2e3d18e0c5ee7602201b83b10ebc4d6dcee3f9eb42ba8f1ef8a059a05397e0c1b9223d1565a3e6ec01012102a7a079c1ef9916b289c2ff21a992c808d0de3dfcf8a9f163205c5c9e21f55d5cffffffff0230750000000000001976a914954820f1de627a703596ac0396f986d958e3de4c88ac10270000000000001976a91405427736705cfbfaff76b1cff48283707fb1037088ac00000000'

    def test_one_three_fee(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC

        inp1 = proto.TxInputType(
            address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
            # amount=390000,
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
        )

        out1 = proto.TxOutputType(
            address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
            amount=390000 - 80000 - 12000 - 10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        out2 = proto.TxOutputType(
            address='13uaUYn6XAooo88QvAqAVsiVvr2mAXutqP',
            amount=12000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        out3 = proto.TxOutputType(
            address_n=[1],
            amount=80000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=2)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=2)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=2)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Bitcoin', [inp1, ], [out1, out2, out3])

        assert hexlify(serialized_tx) == b'010000000182488650ef25a58fef6788bd71b8212038d7f2bbe4750bc7bcb44701e85ef6d5000000006b483045022100e695e2c530c7c0fc32e6b79b7cff56a7f70a8c9da787534f46b4204070f914fc02207b0879a81408a11e23b11d4c7965c62b5fc6d5c2d92340f5ee2da7b40e99314a0121023230848585885f63803a0a8aecdd6538792d5c539215c91698e315bf0253b43dffffffff0300650400000000001976a914de9b2a8da088824e8fe51debea566617d851537888ace02e0000000000001976a9141fe1d337fb81afca42818051e12fd18245d1b17288ac80380100000000001976a9140223b1a09138753c9cb0baf95a0a62c82711567a88ac00000000'

    def test_two_two(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # tx: c6be22d34946593bcad1d2b013e12f74159e69574ffea21581dad115572e031c
        # input 1: 0.0010 BTC
        # tx: 58497a7757224d1ff1941488d23087071103e5bf855f4c1c44e5c8d9d82ca46e
        # input 1: 0.0011 BTC

        inp1 = proto.TxInputType(
            address_n=[1],  # 1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb
            # amount=100000,
            prev_hash=TXHASH_c6be22,
            prev_index=1,
        )

        inp2 = proto.TxInputType(
            address_n=[2],  # 15AeAhtNJNKyowK8qPHwgpXkhsokzLtUpG
            # amount=110000,
            prev_hash=TXHASH_58497a,
            prev_index=1,
        )

        out1 = proto.TxOutputType(
            address='15Jvu3nZNP7u2ipw2533Q9VVgEu2Lu9F2B',
            amount=210000 - 100000 - 10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        out2 = proto.TxOutputType(
            address_n=[3],  # 1CmzyJp9w3NafXMSEFH4SLYUPAVCSUrrJ5
            amount=100000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_c6be22)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_c6be22)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_c6be22)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_c6be22)),

                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_58497a)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_58497a)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_58497a)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_58497a)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Bitcoin', [inp1, inp2], [out1, out2])

        # Accepted by network: tx c63e24ed820c5851b60c54613fbc4bcb37df6cd49b4c96143e99580a472f79fb
        assert hexlify(serialized_tx) == b'01000000021c032e5715d1da8115a2fe4f57699e15742fe113b0d2d1ca3b594649d322bec6010000006b483045022100f773c403b2f85a5c1d6c9c4ad69c43de66930fff4b1bc818eb257af98305546a0220443bde4be439f276a6ce793664b463580e210ec6c9255d68354449ac0443c76501210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6ffffffff6ea42cd8d9c8e5441c4c5f85bfe50311078730d2881494f11f4d2257777a4958010000006b48304502210090cff1c1911e771605358a8cddd5ae94c7b60cc96e50275908d9bf9d6367c79f02202bfa72e10260a146abd59d0526e1335bacfbb2b4401780e9e3a7441b0480c8da0121038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e3ffffffff02a0860100000000001976a9142f4490d5263906e4887ca2996b9e207af3e7824088aca0860100000000001976a914812c13d97f9159e54e326b481b8f88a73df8507a88ac00000000'

    """
    def test_lots_of_inputs(self):
        self.setup_mnemonic_nopin_nopassphrase()
        # Tests if device implements serialization of len(inputs) correctly
        # tx 4a7b7e0403ae5607e473949cfa03f09f2cd8b0f404bf99ce10b7303d86280bf7 : 100 UTXO for spending for unit tests
        inputs = []
        for i in range(100):
            inputs.append( proto.TxInputType(address_n=[4], # 1NwN6UduuVkJi6sw3gSiKZaCY5rHgVXC2h
                                                   prev_hash=TXHASH_4a7b7e,
                                                   prev_index=i) )
        out = proto.TxOutputType(address='19dvDdyxxptP9dGvozYe8BP6tgFV9L4jg5',
                                       amount=100 * 26000 - 15 * 10000,
                                       script_type=proto.OutputScriptType.PAYTOADDRESS)
        with self.client:
            (signatures, serialized_tx) = self.client.sign_tx('Bitcoin', inputs, [out])
        # Accepted by network: tx 23d9d8eecf3abf6c0f0f3f8b0976a04792d7f1c9a4ea9b0a8931734949e27c92
        # too big put in unit test
    """

    def test_lots_of_outputs(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # Tests if device implements serialization of len(outputs) correctly

        # tx: c63e24ed820c5851b60c54613fbc4bcb37df6cd49b4c96143e99580a472f79fb
        # index 1: 0.0010 BTC
        # tx: 39a29e954977662ab3879c66fb251ef753e0912223a83d1dcb009111d28265e5
        # index 1: 0.0254 BTC

        inp1 = proto.TxInputType(
            address_n=[3],  # 1CmzyJp9w3NafXMSEFH4SLYUPAVCSUrrJ5
            # amount=100000,
            prev_hash=TXHASH_c63e24,
            prev_index=1,
        )

        inp2 = proto.TxInputType(
            address_n=[3],  # 1CmzyJp9w3NafXMSEFH4SLYUPAVCSUrrJ5
            # amount=2540000,
            prev_hash=TXHASH_39a29e,
            prev_index=1,
        )

        outputs = []
        cnt = 255
        for _ in range(cnt):
            out = proto.TxOutputType(
                address='1NwN6UduuVkJi6sw3gSiKZaCY5rHgVXC2h',
                amount=(100000 + 2540000 - 39000) // cnt,
                script_type=proto.OutputScriptType.PAYTOADDRESS,
            )
            outputs.append(out)

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_c63e24)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_c63e24)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_c63e24)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_c63e24)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_c63e24)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_39a29e)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_39a29e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_39a29e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_39a29e)),
            ] + [
                item for items in zip(
                    [proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=I)) for I in range(cnt)],
                    [proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput)] * cnt
                ) for item in items
            ] + [
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
            ] + [
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=I)) for I in range(cnt)
            ] + [
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
            ] + [
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=I)) for I in range(cnt)
            ] + [
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=I)) for I in range(cnt)
            ] + [
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Bitcoin', [inp1, inp2], outputs)

        if cnt == 255:
            assert hexlify(serialized_tx) == b'0100000002fb792f470a58993e14964c9bd46cdf37cb4bbc3f61540cb651580c82ed243ec6010000006b483045022100969da46f94a81f34f3717b014e0c3e1826eda1b0022ec2f9ce39f3d750ab9235022026da269770993211a1503413566a339bbb4389a482fffcf8e1f76713fc3b94f5012103477b9f0f34ae85434ce795f0c5e1e90c9420e5b5fad084d7cce9a487b94a7902ffffffffe56582d2119100cb1d3da8232291e053f71e25fb669c87b32a667749959ea239010000006a473044022052e1419bb237b9db400ab5e3df16db6355619d545fde9030924a360763ae9ad40220704beab04d72ecaeb42eca7d98faca7a0941e65f2e1341f183be2b83e6b09e1c012103477b9f0f34ae85434ce795f0c5e1e90c9420e5b5fad084d7cce9a487b94a7902fffffffffdff00' + b'd8270000000000001976a914f0a2b64e56ee2ff57126232f84af6e3a41d4055088ac' * cnt + b'00000000'

    def test_fee_too_high(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # tx: 1570416eb4302cf52979afd5e6909e37d8fdd874301f7cc87e547e509cb1caa6
        # input 0: 1.0 BTC

        inp1 = proto.TxInputType(
            address_n=[0],  # 1HWDaLTpTCTtRWyWqZkzWx1wex5NKyncLW
            # amount=100000000,
            prev_hash=TXHASH_157041,
            prev_index=0,
        )

        out1 = proto.TxOutputType(
            address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
            amount=100000000 - 510000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_157041)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_157041)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_157041)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_157041)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.FeeOverThreshold),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Bitcoin', [inp1, ], [out1, ])

        assert hexlify(serialized_tx) == b'0100000001a6cab19c507e547ec87c1f3074d8fdd8379e90e6d5af7929f52c30b46e417015000000006b483045022100dc3531da7feb261575f03b5b9bbb35edc7f73bb081c92538827105de4102737002200161e34395f6a8ee93979200cb974fa75ccef6d7c14021511cf468eece90d6450121023230848585885f63803a0a8aecdd6538792d5c539215c91698e315bf0253b43dffffffff01d018ee05000000001976a914de9b2a8da088824e8fe51debea566617d851537888ac00000000'

    def test_not_enough_funds(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
        # input 0: 0.0039 BTC

        inp1 = proto.TxInputType(
            address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
            # amount=390000,
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
        )

        out1 = proto.TxOutputType(
            address='1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1',
            amount=400000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_d5f65e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.Failure(code=proto.FailureType.NotEnoughFunds)
            ])

            try:
                self.client.sign_tx('Bitcoin', [inp1, ], [out1, ])
            except CallException as e:
                assert e.args[0] == proto.FailureType.NotEnoughFunds
            else:
                assert False  # types.FailureType.NotEnoughFunds expected

    def test_p2sh(self):
        self.setup_mnemonic_nopin_nopassphrase()

        inp1 = proto.TxInputType(
            address_n=[0],  # 14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e
            # amount=400000,
            prev_hash=TXHASH_54aa56,
            prev_index=1,
        )

        out1 = proto.TxOutputType(
            address='3DKGE1pvPpBAgZj94MbCinwmksewUNNYVR',  # p2sh
            amount=400000 - 10000,
            script_type=proto.OutputScriptType.PAYTOSCRIPTHASH,
        )

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_54aa56)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_54aa56)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_54aa56)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_54aa56)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Bitcoin', [inp1, ], [out1, ])

        # Accepted by network: tx 8cc1f4adf7224ce855cf535a5104594a0004cb3b640d6714fdb00b9128832dd5
        assert hexlify(serialized_tx) == b'0100000001a3fb2d38322c3b327e54005cebc0686d52fcdf536e53bb5ef481a7de8056aa54010000006b4830450221009e020b0390ccad533b73b552f8a99a9d827212c558e4f755503674d07c92ad4502202d606f7316990e0461c51d4add25054f19c697aa3e3c2ced4d568f0b2c57e62f0121023230848585885f63803a0a8aecdd6538792d5c539215c91698e315bf0253b43dffffffff0170f305000000000017a9147f844bdb0b8fd54b64e3d16c85dc1170f1ff97c18700000000'

    def test_attack_change_outputs(self):
        # This unit test attempts to modify data sent during ping-pong of streaming signing.
        # Because device is asking for human confirmation only during first pass (first input),
        # device must detect that data has been modified during other passes and fail to sign
        # such modified data (which has not been confirmed by the user).

        # Test firstly prepare normal transaction and send it to device. Then it send the same
        # transaction again, but change amount of output 1 during signing the second input.

        self.setup_mnemonic_nopin_nopassphrase()

        inp1 = proto.TxInputType(
            address_n=[1],  # 1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb
            # amount=100000,
            prev_hash=TXHASH_c6be22,
            prev_index=1,
        )

        inp2 = proto.TxInputType(
            address_n=[2],  # 15AeAhtNJNKyowK8qPHwgpXkhsokzLtUpG
            # amount=110000,
            prev_hash=TXHASH_58497a,
            prev_index=1,
        )

        out1 = proto.TxOutputType(
            address='15Jvu3nZNP7u2ipw2533Q9VVgEu2Lu9F2B',
            amount=210000 - 100000 - 10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        out2 = proto.TxOutputType(
            address_n=[3],  # 1CmzyJp9w3NafXMSEFH4SLYUPAVCSUrrJ5
            amount=100000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        global run_attack
        run_attack = False

        def attack_processor(req, msg):
            global run_attack

            if req.details.tx_hash is not None:
                return msg

            if req.details.request_index != 1:
                return msg

            if req.request_type != proto.RequestType.TXOUTPUT:
                return msg

            if not run_attack:
                run_attack = True
                return msg

            msg.outputs[0].amount = 9999999  # Sign output with another amount
            return msg

        # Test if the transaction can be signed normally
        (_, serialized_tx) = self.client.sign_tx('Bitcoin', [inp1, inp2], [out1, out2])

        # Accepted by network: tx c63e24ed820c5851b60c54613fbc4bcb37df6cd49b4c96143e99580a472f79fb
        assert hexlify(serialized_tx) == b'01000000021c032e5715d1da8115a2fe4f57699e15742fe113b0d2d1ca3b594649d322bec6010000006b483045022100f773c403b2f85a5c1d6c9c4ad69c43de66930fff4b1bc818eb257af98305546a0220443bde4be439f276a6ce793664b463580e210ec6c9255d68354449ac0443c76501210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6ffffffff6ea42cd8d9c8e5441c4c5f85bfe50311078730d2881494f11f4d2257777a4958010000006b48304502210090cff1c1911e771605358a8cddd5ae94c7b60cc96e50275908d9bf9d6367c79f02202bfa72e10260a146abd59d0526e1335bacfbb2b4401780e9e3a7441b0480c8da0121038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e3ffffffff02a0860100000000001976a9142f4490d5263906e4887ca2996b9e207af3e7824088aca0860100000000001976a914812c13d97f9159e54e326b481b8f88a73df8507a88ac00000000'

        # Now run the attack, must trigger the exception
        try:
            self.client.sign_tx('Bitcoin', [inp1, inp2], [out1, out2], debug_processor=attack_processor)
        except CallException as exc:
            assert exc.args[0] == proto.FailureType.ProcessError
            assert exc.args[1] == 'Transaction has changed during signing'
        else:
            assert False  # exception expected

    def test_attack_change_input_address(self):
        # This unit test attempts to modify input address after the Trezor checked
        # that it matches the change output

        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiTestnet)

        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/1'/4'/0/0"),
            # moUJnmge8SRXuediK7bW6t4YfrPqbE6hD7
            prev_hash=TXHASH_d2dcda,
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )

        out1 = proto.TxOutputType(
            address='mwue7mokpBRAsJtHqEMcRPanYBmsSmYKvY',
            amount=100000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        out2 = proto.TxOutputType(
            address_n=self.client.expand_path("44'/1'/12345'/1/0"),
            amount=123400000 - 5000 - 100000,
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

            msg.inputs[0].address_n[2] = 12345 + 0x80000000
            run_attack = False
            return msg

        # Test if the transaction can be signed normally
        (_, serialized_tx) = self.client.sign_tx('Testnet', [inp1], [out1, out2])

        assert hexlify(serialized_tx) == b'0100000001243e15b53cc553d93ec4e27e16984adc3d885ef107c613a7577fea47f5dadcd2010000006a47304402207d517dcb6b823bba4d252da096795a7f914d0c477aee26e554ba61653c45608a02202cba1e805c586c830472f399510be5d42c2fcfd67b8a6b0690cbe8a3e6e475e801210364430c9122948e525e2f1c6d88f00f47679274f0810fd8c63754954f310995c1ffffffff02a0860100000000001976a914b3cc67f3349974d0f1b50e9bb5dfdf226f888fa088ac18555907000000001976a91485a3f5b0d23cdd61f5f8e1eb8c9ca0890dd15a9788ac00000000'

        # Now run the attack, must trigger the exception
        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_d2dcda)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_d2dcda)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_d2dcda)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_d2dcda)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.Failure(code=proto.FailureType.ProcessError),
            ])
            # Now run the attack, must trigger the exception
            try:
                self.client.sign_tx('Testnet', [inp1], [out1, out2], debug_processor=attack_processor)
            except CallException as exc:
                assert exc.args[0] == proto.FailureType.ProcessError
                assert exc.args[1] == 'Transaction has changed during signing'
            else:
                assert False  # exception expected

    def test_spend_coinbase(self):
        # 25 TEST generated to m/1 (mfiGQVPcRcaEvQPYDErR34DcCovtxYvUUV)
        # tx: d6da21677d7cca5f42fbc7631d062c9ae918a0254f7c6c22de8e8cb7fd5b8236
        # input 0: 25.0027823 BTC

        self.setup_mnemonic_nopin_nopassphrase()

        inp1 = proto.TxInputType(
            address_n=[1],  # mfiGQVPcRcaEvQPYDErR34DcCovtxYvUUV
            # amount=390000,
            prev_hash=TXHASH_d6da21,
            prev_index=0,
        )

        out1 = proto.TxOutputType(
            address='mm6FM31rM5Vc3sw5D7kztiBg3jHUzyqF1g',
            amount=2500278230 - 10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_tx_api(TxApiTestnet)
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_d6da21)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_d6da21)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_d6da21)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx('Testnet', [inp1, ], [out1, ])

        # Accepted by network: tx
        assert hexlify(serialized_tx) == b'010000000136825bfdb78c8ede226c7c4f25a018e99a2c061d63c7fb425fca7c7d6721dad6000000006a473044022047845c366eb24f40be315c7815a154513c444c7989eb80f7ce7ff6aeb703d26a022007c1f5efadf67c5889634fd7ac39a7ce78bffac291673e8772ecd8389c901d9f01210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6ffffffff01c6100795000000001976a9143d2496e67f5f57a924353da42d4725b318e7a8ea88ac00000000'

    def test_two_changes(self):
        self.setup_mnemonic_allallall()
        # see 87be0736f202f7c2bff0781b42bad3e0cdcb54761939da69ea793a3735552c56

        # tx: e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd
        # input 0: 0.31 BTC
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/1'/0'/0/0"),
            # amount=31000000,
            prev_hash=TXHASH_e5040e,
            prev_index=0,
        )

        out1 = proto.TxOutputType(
            address='msj42CCGruhRsFrGATiUuh25dtxYtnpbTx',
            amount=30090000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        out_change1 = proto.TxOutputType(
            address_n=self.client.expand_path("44'/1'/0'/1/0"),
            amount=900000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        out_change2 = proto.TxOutputType(
            address_n=self.client.expand_path("44'/1'/0'/1/1"),
            amount=10000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_tx_api(TxApiTestnet)
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_e5040e)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_e5040e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_e5040e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_e5040e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=2)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),

                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=2)),

                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=2)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])

            self.client.sign_tx('Testnet', [inp1, ], [out1, out_change1, out_change2])

    def test_change_on_main_chain_allowed(self):
        self.setup_mnemonic_allallall()
        # see 87be0736f202f7c2bff0781b42bad3e0cdcb54761939da69ea793a3735552c56

        # tx: e5040e1bc1ae7667ffb9e5248e90b2fb93cd9150234151ce90e14ab2f5933bcd
        # input 0: 0.31 BTC
        inp1 = proto.TxInputType(
            address_n=self.client.expand_path("44'/1'/0'/0/0"),
            # amount=31000000,
            prev_hash=TXHASH_e5040e,
            prev_index=0,
        )

        out1 = proto.TxOutputType(
            address='msj42CCGruhRsFrGATiUuh25dtxYtnpbTx',
            amount=30090000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        # change on main chain is allowed => treated as a change
        out_change = proto.TxOutputType(
            address_n=self.client.expand_path("44'/1'/0'/0/0"),
            amount=900000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with self.client:
            self.client.set_tx_api(TxApiTestnet)
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_e5040e)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_e5040e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0, tx_hash=TXHASH_e5040e)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1, tx_hash=TXHASH_e5040e)),

                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),

                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),

                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])

            self.client.sign_tx('Testnet', [inp1, ], [out1, out_change])
