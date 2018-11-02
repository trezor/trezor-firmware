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

TX_API = tx_cache("Decred Testnet")


TXHASH_e16248 = bytes.fromhex(
    "e16248f0b39a0a0c0e53d6f2f84c2a944f0d50e017a82701e8e02e46e979d5ed"
)
TXHASH_5e6e35 = bytes.fromhex(
    "5e6e3500a333c53c02f523db5f1a9b17538a8850b4c2c24ecb9b7ba48059b970"
)
TXHASH_ccf95b = bytes.fromhex(
    "ccf95b0fd220ef59ae2e5b17005a81e222758122682d522eff8ae1fcbc93bc74"
)
TXHASH_f395ef = bytes.fromhex(
    "f395ef3e72a831a766db15e7a38bc28025d4ee02234d68bdea2d8353b47a3113"
)
TXHASH_3f7c39 = bytes.fromhex(
    "3f7c395521d38387e7617565fe17628723ef6635a08537ad9c46cfb1619e4c3f"
)
TXHASH_16da18 = bytes.fromhex(
    "16da185052740d85a630e79c140558215b64e26c500212b90e16b55d13ca06a8"
)


@pytest.mark.decred
class TestMsgSigntxDecred(TrezorTest):
    def test_send_decred(self):
        self.setup_mnemonic_allallall()

        inp1 = proto.TxInputType(
            # TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz
            address_n=parse_path("m/44'/1'/0'/0/0"),
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
            self.client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=TXHASH_e16248),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            tx_hash=TXHASH_e16248, request_index=0
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            tx_hash=TXHASH_e16248, request_index=0
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            tx_hash=TXHASH_e16248, request_index=1
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.FeeOverThreshold),
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                self.client, "Decred Testnet", [inp1], [out1], prev_txes=TX_API
            )

        assert (
            serialized_tx.hex()
            == "0100000001edd579e9462ee0e80127a817e0500d4f942a4cf8f2d6530e0c0a9ab3f04862e10100000000ffffffff01802b530b0000000000001976a914819d291a2f7fbf770e784bfd78b5ce92c58e95ea88ac000000000000000001000000000000000000000000ffffffff6a473044022009e394c7dec76ab6988270b467839b1462ad781556bce37383b76e026418ce6302204f7f6ef535d2986b095d7c96232a0990a0b9ce3004894b39c167bb18e5833ac30121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
        )

    def test_send_decred_change(self):
        self.setup_mnemonic_allallall()

        inp1 = proto.TxInputType(
            # TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz
            address_n=parse_path("m/44'/1'/0'/0/0"),
            prev_hash=TXHASH_5e6e35,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
            decred_tree=0,
        )

        inp2 = proto.TxInputType(
            # TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz
            address_n=parse_path("m/44'/1'/0'/0/0"),
            prev_hash=TXHASH_ccf95b,
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
            decred_tree=0,
        )

        inp3 = proto.TxInputType(
            # Tskt39YEvzoJ5KBDH4f1auNzG3jViVjZ2RV
            address_n=parse_path("m/44'/1'/0'/0/1"),
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
            address_n=parse_path("m/44'/1'/0'/1/0"),
            amount=100000000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
            decred_script_version=0,
        )

        with self.client:
            self.client.set_expected_responses(
                [
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=0),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=TXHASH_5e6e35),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            tx_hash=TXHASH_5e6e35, request_index=0
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            tx_hash=TXHASH_5e6e35, request_index=0
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=TXHASH_ccf95b),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            tx_hash=TXHASH_ccf95b, request_index=0
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            tx_hash=TXHASH_ccf95b, request_index=0
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            tx_hash=TXHASH_ccf95b, request_index=1
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=2),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXMETA,
                        details=proto.TxRequestDetailsType(tx_hash=TXHASH_f395ef),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(
                            tx_hash=TXHASH_f395ef, request_index=0
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            tx_hash=TXHASH_f395ef, request_index=0
                        ),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXOUTPUT,
                        details=proto.TxRequestDetailsType(
                            tx_hash=TXHASH_f395ef, request_index=1
                        ),
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
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=1),
                    ),
                    proto.TxRequest(
                        request_type=proto.RequestType.TXINPUT,
                        details=proto.TxRequestDetailsType(request_index=2),
                    ),
                    proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                self.client,
                "Decred Testnet",
                [inp1, inp2, inp3],
                [out1, out2],
                prev_txes=TX_API,
            )

        assert (
            serialized_tx.hex()
            == "010000000370b95980a47b9bcb4ec2c2b450888a53179b1a5fdb23f5023cc533a300356e5e0000000000ffffffff74bc93bcfce18aff2e522d6822817522e2815a00175b2eae59ef20d20f5bf9cc0100000000ffffffff13317ab453832deabd684d2302eed42580c28ba3e715db66a731a8723eef95f30000000000ffffffff02d86c341d0000000000001976a9143eb656115197956125365348c542e37b6d3d259988ac00e1f5050000000000001976a9143ee6f9d662e7be18373d80e5eb44627014c2bf6688ac000000000000000003000000000000000000000000ffffffff6a47304402200e50a6d43c462045917792e7d03b4354900c3baccb7abef66f556a32b12f2ca6022031ae94fdf2a41dd6ed2e081faf0f8f1c64411a1b46eb26f7f35d94402b2bde110121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0000000000000000000000000ffffffff6a47304402204894c2f8e76c4645d2df600cdd01443aeb48807b72150c4bc10eebd126529532022054cd37462a3f0ddb85c75b4e874ab0c2aad7eebcff3e6c1ac20e1c16babe36720121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0000000000000000000000000ffffffff6b4830450221009f1ba584023da8aafd57374e83be68f1a097b906967ec9e50736f31bfc7989f102204a190fc2885e394572b5c2ced046657b1dd07abdb19144e21e78987968c7f17601210294e3e5e77e22eea0e4c0d30d89beb4db7f69b4bf1ae709e411d6a06618b8f852"
        )

    def test_decred_multisig_change(self):
        self.setup_mnemonic_allallall()

        paths = [parse_path("m/48'/1'/%d'" % index) for index in range(3)]
        nodes = [
            btc.get_public_node(self.client, address_n, coin_name="Decred Testnet").node
            for address_n in paths
        ]

        signatures = [[b"", b"", b""], [b"", b"", b""]]

        def create_multisig(index, address, signatures=None):
            address_n = parse_path(address)
            multisig = proto.MultisigRedeemScriptType(
                pubkeys=[
                    proto.HDNodePathType(node=node, address_n=address_n)
                    for node in nodes
                ],
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
                self.client.set_expected_responses(
                    [
                        proto.TxRequest(
                            request_type=proto.RequestType.TXINPUT,
                            details=proto.TxRequestDetailsType(request_index=0),
                        ),
                        proto.TxRequest(
                            request_type=proto.RequestType.TXMETA,
                            details=proto.TxRequestDetailsType(tx_hash=TXHASH_3f7c39),
                        ),
                        proto.TxRequest(
                            request_type=proto.RequestType.TXINPUT,
                            details=proto.TxRequestDetailsType(
                                tx_hash=TXHASH_3f7c39, request_index=0
                            ),
                        ),
                        proto.TxRequest(
                            request_type=proto.RequestType.TXOUTPUT,
                            details=proto.TxRequestDetailsType(
                                tx_hash=TXHASH_3f7c39, request_index=0
                            ),
                        ),
                        proto.TxRequest(
                            request_type=proto.RequestType.TXOUTPUT,
                            details=proto.TxRequestDetailsType(
                                tx_hash=TXHASH_3f7c39, request_index=1
                            ),
                        ),
                        proto.TxRequest(
                            request_type=proto.RequestType.TXINPUT,
                            details=proto.TxRequestDetailsType(request_index=1),
                        ),
                        proto.TxRequest(
                            request_type=proto.RequestType.TXMETA,
                            details=proto.TxRequestDetailsType(tx_hash=TXHASH_16da18),
                        ),
                        proto.TxRequest(
                            request_type=proto.RequestType.TXINPUT,
                            details=proto.TxRequestDetailsType(
                                tx_hash=TXHASH_16da18, request_index=0
                            ),
                        ),
                        proto.TxRequest(
                            request_type=proto.RequestType.TXOUTPUT,
                            details=proto.TxRequestDetailsType(
                                tx_hash=TXHASH_16da18, request_index=0
                            ),
                        ),
                        proto.TxRequest(
                            request_type=proto.RequestType.TXOUTPUT,
                            details=proto.TxRequestDetailsType(
                                tx_hash=TXHASH_16da18, request_index=1
                            ),
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
                            request_type=proto.RequestType.TXINPUT,
                            details=proto.TxRequestDetailsType(request_index=1),
                        ),
                        proto.TxRequest(request_type=proto.RequestType.TXFINISHED),
                    ]
                )
                signature, serialized_tx = btc.sign_tx(
                    self.client,
                    "Decred Testnet",
                    [inp1, inp2],
                    [out1, out2],
                    prev_txes=TX_API,
                )

            signatures[0][index] = signature[0]
            signatures[1][index] = signature[1]
            return serialized_tx

        test_multisig(2)
        serialized_tx = test_multisig(0)

        assert (
            serialized_tx.hex()
            == "01000000023f4c9e61b1cf469cad3785a03566ef23876217fe657561e78783d32155397c3f0100000000ffffffffa806ca135db5160eb91202506ce2645b215805149ce730a6850d74525018da160000000000ffffffff02605af40500000000000017a9142eea8efc154375a0e95fa7849a84cbce38fc9e138700a3e1110000000000001976a9143eb656115197956125365348c542e37b6d3d259988ac000000000000000002000000000000000000000000fffffffffb47304402205aa748d00fbf632fb85bdb31f52713413d455c560aca2243d3ad6605ee6c590c02200c15581cd87a3454a2f1cccf9660d3a3af94763133721202992e8e44ac9051cd01473044022030ee91f21a813dc36af48da4c57c0043c08c6669b831f4b45e1fb62bf627992c02205643c5150e47528d696cc912d7f542788c31affdf903e38f70f97f4056805b3f014c69522102af12ddd0d55e4fa2fcd084148eaf5b0b641320d0431d63d1e9a90f3cbd0d54072102b952c919f91b8252fc1ccd3aed5c16364e19f11063a9c0da35c7142cc5d5dea4210386037d07c629b9a6cd9e966894527f6bfaf6a13e5c18396f536d360ecae35b7c53ae000000000000000000000000fffffffffc4730440220643f64dcdfe8ed70120f6bb7b32b57acf2136e82f74a88baa8d5603448dd46f9022000f324eba92d79d688afff68704600949bd2f8f47f6fa932e333810b19efe8d701483045022100fe8e52118e769af69028b47acb62d21c3f9f417afa5d217d8351b26c942c9bf5022020ae88a2fa109be7e3ba3936db1435a3e04123e91811949d166d9c808f45f681014c69522102faf963264abfdc1907f0fbfea80e2d7b79c6e017b57ad9f18e89222382137440210240f15dc02925879548f66c8cfde23309dfda287a50b277bd6a4c736725a699592102f1897184f21c582fcf1dabcc15c87668de7ca98b32579b9d092ce4b4db0e16c053ae"
        )
