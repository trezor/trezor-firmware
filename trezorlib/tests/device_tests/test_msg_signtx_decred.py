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

from .common import *

from trezorlib import messages as proto
from trezorlib.tx_api import TxApiDecredTestnet


TXHASH_e16248 = unhexlify("e16248f0b39a0a0c0e53d6f2f84c2a944f0d50e017a82701e8e02e46e979d5ed")
TXHASH_5e6e35 = unhexlify("5e6e3500a333c53c02f523db5f1a9b17538a8850b4c2c24ecb9b7ba48059b970")
TXHASH_ccf95b = unhexlify("ccf95b0fd220ef59ae2e5b17005a81e222758122682d522eff8ae1fcbc93bc74")
TXHASH_f395ef = unhexlify("f395ef3e72a831a766db15e7a38bc28025d4ee02234d68bdea2d8353b47a3113")
TXHASH_3f7c39 = unhexlify("3f7c395521d38387e7617565fe17628723ef6635a08537ad9c46cfb1619e4c3f")
TXHASH_16da18 = unhexlify("16da185052740d85a630e79c140558215b64e26c500212b90e16b55d13ca06a8")


@pytest.mark.skip_t1
@pytest.mark.skip_t2
class TestMsgSigntxDecred(TrezorTest):

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
        assert serialized_tx == unhexlify("0100000001edd579e9462ee0e80127a817e0500d4f942a4cf8f2d6530e0c0a9ab3f04862e10100000000ffffffff01802b530b0000000000001976a914819d291a2f7fbf770e784bfd78b5ce92c58e95ea88ac000000000000000001000000000000000000000000ffffffff6b483045022100bad68486491e449a731513805c129201d7f65601d6f07c97fda0588453c97d22022013e9ef59657ae4f344ac4f0db2b7a23dbfcdb51ebeb85277146ac189e547d3f7012102f5a745afb96077c071e4d19911a5d3d024faa1314ee8688bc6eec39751d0818f")

    def test_send_decred_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiDecredTestnet)

        inp1 = proto.TxInputType(
            # TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz
            address_n=self.client.expand_path("m/44'/1'/0'/0/0"),
            prev_hash=TXHASH_5e6e35,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
            decred_tree=0,
        )

        inp2 = proto.TxInputType(
            # TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz
            address_n=self.client.expand_path("m/44'/1'/0'/0/0"),
            prev_hash=TXHASH_ccf95b,
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
            decred_tree=0,
        )

        inp3 = proto.TxInputType(
            # Tskt39YEvzoJ5KBDH4f1auNzG3jViVjZ2RV
            address_n=self.client.expand_path("m/44'/1'/0'/0/1"),
            prev_hash=TXHASH_f395ef,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
            decred_tree=0,
        )

        out1 = proto.TxOutputType(
            address="TsWjioPrP8E1TuTMmTrVMM2BA4iPrjQXBpR",
            amount=489975000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
            decred_script_version=0,
        )

        out2 = proto.TxOutputType(
            # TsaSFRwfN9muW5F6ZX36iSksc9hruiC5F97
            address_n=self.client.expand_path("m/44'/1'/0'/1/0"),
            amount=100000000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
            decred_script_version=0,
        )

        with self.client:
            self.client.set_expected_responses([
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_5e6e35)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_5e6e35, request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_5e6e35, request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_ccf95b)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_ccf95b, request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_ccf95b, request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_ccf95b, request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=2)),
                proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_f395ef)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_f395ef, request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_f395ef, request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_f395ef, request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
                proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=2)),
                proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
            ])
            (signatures, serialized_tx) = self.client.sign_tx("Decred Testnet", [inp1, inp2, inp3], [out1, out2])

        # Accepted by network: c5ff767141a162b665acf775fcc35b60ff622fbe21a21e0a6609ed768c3737f4
        assert serialized_tx == unhexlify("010000000370b95980a47b9bcb4ec2c2b450888a53179b1a5fdb23f5023cc533a300356e5e0000000000ffffffff74bc93bcfce18aff2e522d6822817522e2815a00175b2eae59ef20d20f5bf9cc0100000000ffffffff13317ab453832deabd684d2302eed42580c28ba3e715db66a731a8723eef95f30000000000ffffffff02d86c341d0000000000001976a9143eb656115197956125365348c542e37b6d3d259988ac00e1f5050000000000001976a9146748ebb8694c069742ee69eab2159c33c7f57d2b88ac000000000000000003000000000000000000000000ffffffff6b483045022100d91237a32b8968e1d3316b76f045cc18fed12736aebd570dd023a61826279cc102204222b133189762368d3398d11eb9a6843a67de11d70ac58426a28b605fa102b1012102f5a745afb96077c071e4d19911a5d3d024faa1314ee8688bc6eec39751d0818f000000000000000000000000ffffffff69463043021f7cf9b0b180f3fcde8d3d036d81e575e368d6ab5c8c6a2ffef47c06a0170023022036b964bf26ff276c58862dfacafa93216618832d6240f16b6100a9d10d5eb753012102f5a745afb96077c071e4d19911a5d3d024faa1314ee8688bc6eec39751d0818f000000000000000000000000ffffffff6b48304502210098f3a0cc17c3383f5998c542950b5cccb1175cc94b8d0343f420dc64abe9a50e0220507974c6ef0761925634fe3e13ec458b8cd3e42856828d584d4a5d39cc4d0f890121022c6099c7af8124d58e97beefc85c529dcfb3865794d46ec04095e70872e32a2e")

    def test_decred_multisig_change(self):
        self.setup_mnemonic_allallall()
        self.client.set_tx_api(TxApiDecredTestnet)

        paths = [self.client.expand_path("m/48'/1'/%d'" % index) for index in range(3)]
        nodes = [self.client.get_public_node(address_n, coin_name="Decred Testnet").node for address_n in paths]

        signatures = [
            [b'', b'', b''],
            [b'', b'', b''],
        ]

        def create_multisig(index, address, signatures=None):
            address_n = self.client.expand_path(address)
            multisig = proto.MultisigRedeemScriptType(
                pubkeys=[proto.HDNodePathType(node=node, address_n=address_n) for node in nodes],
                signatures=signatures,
                m=2,
            )

            return (paths[index] + address_n), multisig

        def test_multisig(index):
            address_n, multisig = create_multisig(index, "m/0/0", signatures[0])
            inp1 = proto.TxInputType(
                address_n=address_n,
                # TchpthUkRys1VQWgnQyLJNaA4MLBjVmRL2c
                multisig=multisig,
                prev_hash=TXHASH_3f7c39,
                prev_index=1,
                script_type=proto.InputScriptType.SPENDMULTISIG,
                decred_tree=0,
            )

            address_n, multisig = create_multisig(index, "m/0/1", signatures[1])
            inp2 = proto.TxInputType(
                address_n=address_n,
                # TcnfDEfMhkM3oLWqiq9v9GmYgLK7qfjitKG
                multisig=multisig,
                prev_hash=TXHASH_16da18,
                prev_index=0,
                script_type=proto.InputScriptType.SPENDMULTISIG,
                decred_tree=0,
            )

            address_n, multisig = create_multisig(index, "m/1/0")
            out1 = proto.TxOutputType(
                address_n=address_n,
                # TcrrURA3Bzj4isGU48PdSP9SDoU5oCpjEcb
                multisig=multisig,
                amount=99900000,
                script_type=proto.OutputScriptType.PAYTOMULTISIG,
                decred_script_version=0,
            )

            out2 = proto.TxOutputType(
                address="TsWjioPrP8E1TuTMmTrVMM2BA4iPrjQXBpR",
                amount=300000000,
                script_type=proto.OutputScriptType.PAYTOADDRESS,
                decred_script_version=0,
            )

            with self.client:
                self.client.set_expected_responses([
                    proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                    proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_3f7c39)),
                    proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_3f7c39, request_index=0)),
                    proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_3f7c39, request_index=0)),
                    proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_3f7c39, request_index=1)),
                    proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
                    proto.TxRequest(request_type=proto.RequestType.TXMETA, details=proto.TxRequestDetailsType(tx_hash=TXHASH_16da18)),
                    proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_16da18, request_index=0)),
                    proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_16da18, request_index=0)),
                    proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(tx_hash=TXHASH_16da18, request_index=1)),
                    proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=0)),
                    proto.TxRequest(request_type=proto.RequestType.TXOUTPUT, details=proto.TxRequestDetailsType(request_index=1)),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=0)),
                    proto.TxRequest(request_type=proto.RequestType.TXINPUT, details=proto.TxRequestDetailsType(request_index=1)),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ])
                (signature, serialized_tx) = self.client.sign_tx("Decred Testnet", [inp1, inp2], [out1, out2])

            signatures[0][index] = signature[0]
            signatures[1][index] = signature[1]
            return serialized_tx

        test_multisig(2)
        serialized_tx = test_multisig(0)

        # Accepted by network: eccfecc0dc3275f7fa5a966b58c8d503f8b3d23964f2ce2c3336e5883919f45f
        assert serialized_tx == unhexlify("01000000023f4c9e61b1cf469cad3785a03566ef23876217fe657561e78783d32155397c3f0100000000ffffffffa806ca135db5160eb91202506ce2645b215805149ce730a6850d74525018da160000000000ffffffff02605af40500000000000017a914d42253369723b43e114b31807ef68f84363e54418700a3e1110000000000001976a9143eb656115197956125365348c542e37b6d3d259988ac000000000000000002000000000000000000000000fffffffffc483045022100be61bbcfd804f1e092c432511884bf8bdc00b6d302f00811149d20628bf3d33502200680721d1d03a71476f65e8815e2fba35bec6be982aa7686a57134eeae9a66f3014730440220016f9dd48ca0ceecf481d96f2c65389abb491af5f0eb63d76eb0f6a67a99718b02204fdeadace9167472411bb44bb63009ebd2373aa77cc08989a25fca37648dc685014c69522102a7ee50c2ceeacaed42aea05b29ac2ac3ec3c7e151dd95780929f53a0011f97a121038f9ebf01b25d80b4b8ad179542859ca96a9c5c8cbf0b5a50a92c0d9a7501efe62103b8d7f5663458e545af7de7a037e61a0e32c291ed2695f3cae120d6a0fe98052e53ae000000000000000000000000fffffffffdfd00483045022100ca8dd36eee86c4cefecfdd91cdf40a35a4274f71c4283e5b98af6bc242e2d5ad022009247ea5663367c2964f61b6111ea1a0790b381a40310f4e867a3725b249f12c01483045022100abc7b1440c31a564e1cd9d0a75abaa5abd8c1285b874c0e97e311e697782954302202fa43fb00149bb2d14b1a31a81b7660d6c9a17c4621a07eb4c2290b627aa540a014c69522103334dd6c58fae3d462f359125f0d6835e57ad885e5058b417f217decc21fdbba4210392af36b8a65ea0bb6f0acdec9069a0b5b75b00d9667b89e2a77f92d4efc92b9821025945b9f11a71546afe4af28cd291830fd77cb184006a90223de1b2c26502bfc353ae")
