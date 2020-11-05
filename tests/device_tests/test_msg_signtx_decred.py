# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

from ..tx_cache import TxCache
from .signtx import request_finished, request_input, request_meta, request_output

B = proto.ButtonRequestType
TX_API = TxCache("Decred Testnet")


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


@pytest.mark.altcoin
@pytest.mark.decred
class TestMsgSigntxDecred:
    def test_send_decred(self, client):
        inp1 = proto.TxInputType(
            # TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz
            address_n=parse_path("m/44'/1'/0'/0/0"),
            prev_hash=TXHASH_e16248,
            prev_index=1,
            amount=200000000,
            script_type=proto.InputScriptType.SPENDADDRESS,
            decred_tree=0,
        )

        out1 = proto.TxOutputType(
            address="TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz",
            amount=190000000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.FeeOverThreshold),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_e16248),
                    request_input(0, TXHASH_e16248),
                    request_output(0, TXHASH_e16248),
                    request_output(1, TXHASH_e16248),
                    request_input(0),
                    request_finished(),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client, "Decred Testnet", [inp1], [out1], prev_txes=TX_API
            )

        assert (
            serialized_tx.hex()
            == "0100000001edd579e9462ee0e80127a817e0500d4f942a4cf8f2d6530e0c0a9ab3f04862e10100000000ffffffff01802b530b0000000000001976a914819d291a2f7fbf770e784bfd78b5ce92c58e95ea88ac00000000000000000100c2eb0b0000000000000000ffffffff6a473044022009e394c7dec76ab6988270b467839b1462ad781556bce37383b76e026418ce6302204f7f6ef535d2986b095d7c96232a0990a0b9ce3004894b39c167bb18e5833ac30121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
        )

    def test_send_decred_change(self, client):
        inp1 = proto.TxInputType(
            # TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz
            address_n=parse_path("m/44'/1'/0'/0/0"),
            amount=190000000,
            prev_hash=TXHASH_5e6e35,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
            decred_tree=0,
        )

        inp2 = proto.TxInputType(
            # TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz
            address_n=parse_path("m/44'/1'/0'/0/0"),
            amount=200000000,
            prev_hash=TXHASH_ccf95b,
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
            decred_tree=0,
        )

        inp3 = proto.TxInputType(
            # Tskt39YEvzoJ5KBDH4f1auNzG3jViVjZ2RV
            address_n=parse_path("m/44'/1'/0'/0/1"),
            amount=200000000,
            prev_hash=TXHASH_f395ef,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
            decred_tree=0,
        )

        out1 = proto.TxOutputType(
            address="TsWjioPrP8E1TuTMmTrVMM2BA4iPrjQXBpR",
            amount=489975000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        out2 = proto.TxOutputType(
            # TsaSFRwfN9muW5F6ZX36iSksc9hruiC5F97
            address_n=parse_path("m/44'/1'/0'/1/0"),
            amount=100000000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_input(1),
                    request_input(2),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    request_output(1),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_5e6e35),
                    request_input(0, TXHASH_5e6e35),
                    request_output(0, TXHASH_5e6e35),
                    request_input(1),
                    request_meta(TXHASH_ccf95b),
                    request_input(0, TXHASH_ccf95b),
                    request_output(0, TXHASH_ccf95b),
                    request_output(1, TXHASH_ccf95b),
                    request_input(2),
                    request_meta(TXHASH_f395ef),
                    request_input(0, TXHASH_f395ef),
                    request_output(0, TXHASH_f395ef),
                    request_output(1, TXHASH_f395ef),
                    request_input(0),
                    request_input(1),
                    request_input(2),
                    request_finished(),
                ]
            )
            _, serialized_tx = btc.sign_tx(
                client,
                "Decred Testnet",
                [inp1, inp2, inp3],
                [out1, out2],
                prev_txes=TX_API,
            )

        assert (
            serialized_tx.hex()
            == "010000000370b95980a47b9bcb4ec2c2b450888a53179b1a5fdb23f5023cc533a300356e5e0000000000ffffffff74bc93bcfce18aff2e522d6822817522e2815a00175b2eae59ef20d20f5bf9cc0100000000ffffffff13317ab453832deabd684d2302eed42580c28ba3e715db66a731a8723eef95f30000000000ffffffff02d86c341d0000000000001976a9143eb656115197956125365348c542e37b6d3d259988ac00e1f5050000000000001976a9143ee6f9d662e7be18373d80e5eb44627014c2bf6688ac000000000000000003802b530b0000000000000000ffffffff6a47304402200e50a6d43c462045917792e7d03b4354900c3baccb7abef66f556a32b12f2ca6022031ae94fdf2a41dd6ed2e081faf0f8f1c64411a1b46eb26f7f35d94402b2bde110121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd000c2eb0b0000000000000000ffffffff6a47304402204894c2f8e76c4645d2df600cdd01443aeb48807b72150c4bc10eebd126529532022054cd37462a3f0ddb85c75b4e874ab0c2aad7eebcff3e6c1ac20e1c16babe36720121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd000c2eb0b0000000000000000ffffffff6b4830450221009f1ba584023da8aafd57374e83be68f1a097b906967ec9e50736f31bfc7989f102204a190fc2885e394572b5c2ced046657b1dd07abdb19144e21e78987968c7f17601210294e3e5e77e22eea0e4c0d30d89beb4db7f69b4bf1ae709e411d6a06618b8f852"
        )

    @pytest.mark.multisig
    def test_decred_multisig_change(self, client):
        paths = [parse_path(f"m/48'/1'/{index}'/0'") for index in range(3)]
        nodes = [
            btc.get_public_node(client, address_n, coin_name="Decred Testnet").node
            for address_n in paths
        ]

        signatures = [[b"", b"", b""], [b"", b"", b""]]

        def create_multisig(index, address, signatures=None):
            address_n = parse_path(address)
            multisig = proto.MultisigRedeemScriptType(
                nodes=nodes, address_n=address_n, signatures=signatures, m=2
            )

            return (paths[index] + address_n), multisig

        def test_multisig(index):
            address_n, multisig = create_multisig(index, "m/0/0", signatures[0])
            inp1 = proto.TxInputType(
                address_n=address_n,
                # TchpthUkRys1VQWgnQyLJNaA4MLBjVmRL2c
                multisig=multisig,
                amount=200000000,
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
                amount=200000000,
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
            )

            out2 = proto.TxOutputType(
                address="TsWjioPrP8E1TuTMmTrVMM2BA4iPrjQXBpR",
                amount=300000000,
                script_type=proto.OutputScriptType.PAYTOADDRESS,
            )

            with client:
                client.set_expected_responses(
                    [
                        request_input(0),
                        request_input(1),
                        request_output(0),
                        request_output(1),
                        proto.ButtonRequest(code=B.ConfirmOutput),
                        proto.ButtonRequest(code=B.SignTx),
                        request_input(0),
                        request_meta(TXHASH_3f7c39),
                        request_input(0, TXHASH_3f7c39),
                        request_output(0, TXHASH_3f7c39),
                        request_output(1, TXHASH_3f7c39),
                        request_input(1),
                        request_meta(TXHASH_16da18),
                        request_input(0, TXHASH_16da18),
                        request_output(0, TXHASH_16da18),
                        request_output(1, TXHASH_16da18),
                        request_input(0),
                        request_input(1),
                        request_finished(),
                    ]
                )
                signature, serialized_tx = btc.sign_tx(
                    client,
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
            == "01000000023f4c9e61b1cf469cad3785a03566ef23876217fe657561e78783d32155397c3f0100000000ffffffffa806ca135db5160eb91202506ce2645b215805149ce730a6850d74525018da160000000000ffffffff02605af40500000000000017a914d4ea4e064d969064ca56a4cede56f7bf6cf62f118700a3e1110000000000001976a9143eb656115197956125365348c542e37b6d3d259988ac00000000000000000200c2eb0b0000000000000000fffffffffc483045022100a35fd1ed579362ac65b583ba910a3d814c5e9b87da835993bf4166a6b3a8482b02204b3e167fad7d37dd62aa585c68d3c8e00c3c43bf7a25d74f6407870a4a7499e9014730440220720fd7b6dfd337056c5e6dad76e307b3758e702ccfd39471bf90e0db3a5f5eba02205bd062c78fcdd56057723a0e39d661a790f325e59e643b54c47b7218a5781684014c69522103defea6f243b97354449bb348446a97e38df2fbed33afc3a7185bfdd26757cfdb2103725d6c5253f2040a9a73af24bcc196bf302d6cc94374dd7197b138e10912670121038924e94fff15302a3fb45ad4fc0ed17178800f0f1c2bdacb1017f4db951aa9f153ae00c2eb0b0000000000000000fffffffffc4730440220625357288f0880be21d6a44275033fd84cf04bc23227eef810455ad711507e4402207d303548bb0476f98c52f223fe4430f82a78a73f757b186453948b0908f5af3101483045022100e140f586e370824b13576c77cf9f2855294fd415316f2a130126d8412a7cf08c0220308d1f5c83847458b271c93bfca5eba7fc1691b9c5d6e57955985affd1110e24014c695221021ef4b5d81f21593071b993bd4d8c564c569a6f84de0d4511135cbc66d8bf7bcd2103f1e53b6e0ff99adf7e8fa826a94bdac83163d8abbc1d19a8d6b88a4af91b9a67210390c8ea70e1f2f60e0052be65183c43bb01b2f02dfa4e448f74e359997f74e6ad53ae"
        )
