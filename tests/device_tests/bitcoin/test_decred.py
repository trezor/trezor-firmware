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

from trezorlib import btc, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...tx_cache import TxCache
from .signtx import request_finished, request_input, request_meta, request_output

B = messages.ButtonRequestType
TX_API = TxCache("Decred Testnet")


FAKE_TXHASH_4d8acd = bytes.fromhex(
    "4d8acde26d5efc7f5df1b3cdada6b11027616520c883e09c919b88f0f0cb6410"
)
FAKE_TXHASH_f341fd = bytes.fromhex(
    "f341fde6a78c2e150619d1c5ecbd90fabeb9e278024cc38ea4190d0b4a6d61d8"
)
FAKE_TXHASH_5f3a7d = bytes.fromhex(
    "5f3a7d29623eba20788e967439c1ccf122688589dfc07cddcedd1b27dc14b568"
)
FAKE_TXHASH_9ac7d2 = bytes.fromhex(
    "9ac7d222f4460ccf4ef38eee047eaf8b3a09505364afe4fe27b765e4c5508fd1"
)
FAKE_TXHASH_48f5b8 = bytes.fromhex(
    "48f5b85f8b1cf796d0d07388ced491f154e2d26b0615529d2d6ba9c170542df3"
)
FAKE_TXHASH_f8e2f2 = bytes.fromhex(
    "f8e2f2b4eab772f6e3743cba92db341f64b84d9c16ae375c7690fbf0bf02fc7b"
)
FAKE_TXHASH_51bc9c = bytes.fromhex(
    "51bc9c71f10a81eef3caedb5333062eb4b1f70998adf02916fe98fdc04c572e8"
)

pytestmark = [pytest.mark.altcoin, pytest.mark.decred, pytest.mark.skip_tr]


def test_send_decred(client: Client):
    # NOTE: fake input tx used

    inp1 = messages.TxInputType(
        # TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz
        address_n=parse_path("m/44h/1h/0h/0/0"),
        prev_hash=FAKE_TXHASH_4d8acd,
        prev_index=1,
        amount=200_000_000,
        script_type=messages.InputScriptType.SPENDADDRESS,
        decred_tree=0,
    )

    out1 = messages.TxOutputType(
        address="TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz",
        amount=190_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.FeeOverThreshold),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(FAKE_TXHASH_4d8acd),
                request_input(0, FAKE_TXHASH_4d8acd),
                request_output(0, FAKE_TXHASH_4d8acd),
                request_output(1, FAKE_TXHASH_4d8acd),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Decred Testnet", [inp1], [out1], prev_txes=TX_API
        )

    assert (
        serialized_tx.hex()
        == "01000000011064cbf0f0889b919ce083c82065612710b1a6adcdb3f15d7ffc5e6de2cd8a4d0100000000ffffffff01802b530b0000000000001976a914819d291a2f7fbf770e784bfd78b5ce92c58e95ea88ac00000000000000000100c2eb0b0000000000000000ffffffff6a47304402202f77445fd8b2d47f6d28fa6087d4bc3ac6986904bf9009c41e527245905d21870220227f463d1dbfba492514e1ee78e32060bfdb4ca9251c4e0557c232e740515eb70121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
    )


@pytest.mark.skip_t1
def test_purchase_ticket_decred(client: Client):
    # NOTE: fake input tx used

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        prev_hash=FAKE_TXHASH_4d8acd,
        prev_index=1,
        amount=200_000_000,
        decred_tree=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )

    out1 = messages.TxOutputType(
        address="TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=199_900_000,
    )
    out2 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=200_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out3 = messages.TxOutputType(
        address="TsR28UZRprhgQQhzWns2M6cAwchrNVvbYq2",
        amount=0,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                request_output(2),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(FAKE_TXHASH_4d8acd),
                request_input(0, FAKE_TXHASH_4d8acd),
                request_output(0, FAKE_TXHASH_4d8acd),
                request_output(1, FAKE_TXHASH_4d8acd),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Decred Testnet",
            [inp1],
            [out1, out2, out3],
            prev_txes=TX_API,
            decred_staking_ticket=True,
        )

    assert (
        serialized_tx.hex()
        == "01000000011064cbf0f0889b919ce083c82065612710b1a6adcdb3f15d7ffc5e6de2cd8a4d0100000000ffffffff03603bea0b0000000000001aba76a914819d291a2f7fbf770e784bfd78b5ce92c58e95ea88ac00000000000000000000206a1edc1a98d791735eb9a8715a2a219c23680edcedad00c2eb0b000000000058000000000000000000001abd76a914000000000000000000000000000000000000000088ac00000000000000000100c2eb0b0000000000000000ffffffff6b483045022100b3a11ff4befcc035623de7665aaa76dacc9252e53aabf2a5d61238151e696532022004cbcc537c1d539e04c823140bac4524bdba09f528f5c4b76f3f1022b7dc0ad40121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
    )


@pytest.mark.skip_t1
def test_spend_from_stake_generation_and_revocation_decred(client: Client):
    # NOTE: fake input tx used

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        prev_hash=FAKE_TXHASH_f8e2f2,
        prev_index=2,
        amount=200_000_000,
        script_type=messages.InputScriptType.SPENDADDRESS,
        decred_staking_spend=messages.DecredStakingSpendType.SSGen,
        decred_tree=1,
    )

    inp2 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        prev_hash=FAKE_TXHASH_51bc9c,
        prev_index=0,
        amount=200_000_000,
        script_type=messages.InputScriptType.SPENDADDRESS,
        decred_staking_spend=messages.DecredStakingSpendType.SSRTX,
        decred_tree=1,
    )

    out1 = messages.TxOutputType(
        address="TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz",
        amount=399_900_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(FAKE_TXHASH_f8e2f2),
                request_input(0, FAKE_TXHASH_f8e2f2),
                request_input(1, FAKE_TXHASH_f8e2f2),
                request_output(0, FAKE_TXHASH_f8e2f2),
                request_output(1, FAKE_TXHASH_f8e2f2),
                request_output(2, FAKE_TXHASH_f8e2f2),
                request_input(1),
                request_meta(FAKE_TXHASH_51bc9c),
                request_input(0, FAKE_TXHASH_51bc9c),
                request_output(0, FAKE_TXHASH_51bc9c),
                request_input(0),
                request_input(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Decred Testnet", [inp1, inp2], [out1], prev_txes=TX_API
        )

    assert (
        serialized_tx.hex()
        == "01000000027bfc02bff0fb90765c37ae169c4db8641f34db92ba3c74e3f672b7eab4f2e2f80200000001ffffffffe872c504dc8fe96f9102df8a99701f4beb623033b5edcaf3ee810af1719cbc510000000001ffffffff0160fdd5170000000000001976a914819d291a2f7fbf770e784bfd78b5ce92c58e95ea88ac00000000000000000200c2eb0b0000000000000000ffffffff6b483045022100f74f652a073bdaf2197ede47b4df0d90609bbfd0dc8a94199d36ebb1429de09b022040366292a8812135ec7572a94eb6e969fa1fa97a52c03f08a337f20bc4fb71de0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd000c2eb0b0000000000000000ffffffff6b483045022100ca385c05a008239c038e107989bbc30eec1ecd5a66e4973265eb21df034c77a9022070c3dceb24b39cb6e9f8c973572b955b37a4754e9caa704cdd37113c46e2b2970121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
    )


def test_send_decred_change(client: Client):
    # NOTE: fake input tx used

    inp1 = messages.TxInputType(
        # TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz
        address_n=parse_path("m/44h/1h/0h/0/0"),
        prev_hash=FAKE_TXHASH_4d8acd,
        prev_index=1,
        amount=200_000_000,
        script_type=messages.InputScriptType.SPENDADDRESS,
        decred_tree=0,
    )

    inp2 = messages.TxInputType(
        # TscqTv1he8MZrV321SfRghw7LFBCJDKB3oz
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=200_000_000,
        prev_hash=FAKE_TXHASH_f341fd,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDADDRESS,
        decred_tree=0,
    )

    inp3 = messages.TxInputType(
        # Tskt39YEvzoJ5KBDH4f1auNzG3jViVjZ2RV
        address_n=parse_path("m/44h/1h/0h/0/1"),
        amount=200_000_000,
        prev_hash=FAKE_TXHASH_5f3a7d,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
        decred_tree=0,
    )

    out1 = messages.TxOutputType(
        address="TsWjioPrP8E1TuTMmTrVMM2BA4iPrjQXBpR",
        amount=499_975_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        # TsaSFRwfN9muW5F6ZX36iSksc9hruiC5F97
        address_n=parse_path("m/44h/1h/0h/1/0"),
        amount=100_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_input(2),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(FAKE_TXHASH_4d8acd),
                request_input(0, FAKE_TXHASH_4d8acd),
                request_output(0, FAKE_TXHASH_4d8acd),
                request_output(1, FAKE_TXHASH_4d8acd),
                request_input(1),
                request_meta(FAKE_TXHASH_f341fd),
                request_input(0, FAKE_TXHASH_f341fd),
                request_output(0, FAKE_TXHASH_f341fd),
                request_output(1, FAKE_TXHASH_f341fd),
                request_input(2),
                request_meta(FAKE_TXHASH_5f3a7d),
                request_input(0, FAKE_TXHASH_5f3a7d),
                request_output(0, FAKE_TXHASH_5f3a7d),
                request_output(1, FAKE_TXHASH_5f3a7d),
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
        == "01000000031064cbf0f0889b919ce083c82065612710b1a6adcdb3f15d7ffc5e6de2cd8a4d0100000000ffffffffd8616d4a0b0d19a48ec34c0278e2b9befa90bdecc5d11906152e8ca7e6fd41f30100000000ffffffff68b514dc271bddcedd7cc0df89856822f1ccc13974968e7820ba3e62297d3a5f0000000000ffffffff025803cd1d0000000000001976a9143eb656115197956125365348c542e37b6d3d259988ac00e1f5050000000000001976a9143ee6f9d662e7be18373d80e5eb44627014c2bf6688ac00000000000000000300c2eb0b0000000000000000ffffffff6a47304402205eec688bd8d52908dae5fa29d121637b6d5c7df0246235a0dbab8170e3d0309e0220774560da627134cb1942a8cafd3926e67317af70287f0c8422468821ea4f78560121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd000c2eb0b0000000000000000ffffffff6a4730440220171d7840fee536f2c41e80bdcd9d2248eadfe32f51e0404582aa9ce8d7c31f5f022075c6fbb39394dd34a6271ada25a9e68dc26ddb46fa84962c40a11fafadf9e2fd0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd000c2eb0b0000000000000000ffffffff6a47304402207121e3da42ec635e3ba9d5c4e7f4921c6acab87c60d58956f60d89eab69defa60220649c2d9a987407e259088e5ebebae289e4b8a82bc77850004978021561299fcc01210294e3e5e77e22eea0e4c0d30d89beb4db7f69b4bf1ae709e411d6a06618b8f852"
    )


@pytest.mark.multisig
def test_decred_multisig_change(client: Client):
    # NOTE: fake input tx used

    paths = [parse_path(f"m/48h/1h/{index}'/0'") for index in range(3)]
    nodes = [
        btc.get_public_node(client, address_n, coin_name="Decred Testnet").node
        for address_n in paths
    ]

    signatures = [[b"", b"", b""], [b"", b"", b""]]

    def create_multisig(index, address, signatures=None):
        address_n = parse_path(address)
        multisig = messages.MultisigRedeemScriptType(
            nodes=nodes, address_n=address_n, signatures=signatures, m=2
        )

        return (paths[index] + address_n), multisig

    def test_multisig(index):
        address_n, multisig = create_multisig(index, "m/0/0", signatures[0])
        inp1 = messages.TxInputType(
            address_n=address_n,
            # TchpthUkRys1VQWgnQyLJNaA4MLBjVmRL2c
            multisig=multisig,
            amount=200_000_000,
            prev_hash=FAKE_TXHASH_9ac7d2,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDMULTISIG,
            decred_tree=0,
        )

        address_n, multisig = create_multisig(index, "m/0/1", signatures[1])
        inp2 = messages.TxInputType(
            address_n=address_n,
            # TcnfDEfMhkM3oLWqiq9v9GmYgLK7qfjitKG
            multisig=multisig,
            amount=200_000_000,
            prev_hash=FAKE_TXHASH_48f5b8,
            prev_index=0,
            script_type=messages.InputScriptType.SPENDMULTISIG,
            decred_tree=0,
        )

        address_n, multisig = create_multisig(index, "m/1/0")
        out1 = messages.TxOutputType(
            address_n=address_n,
            # TcrrURA3Bzj4isGU48PdSP9SDoU5oCpjEcb
            multisig=multisig,
            amount=99_900_000,
            script_type=messages.OutputScriptType.PAYTOMULTISIG,
        )

        out2 = messages.TxOutputType(
            address="TsWjioPrP8E1TuTMmTrVMM2BA4iPrjQXBpR",
            amount=300_000_000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            is_core = client.features.model in ("T", "Safe 3")
            client.set_expected_responses(
                [
                    request_input(0),
                    request_input(1),
                    request_output(0),
                    request_output(1),
                    messages.ButtonRequest(code=B.ConfirmOutput),
                    (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                    messages.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(FAKE_TXHASH_9ac7d2),
                    request_input(0, FAKE_TXHASH_9ac7d2),
                    request_output(0, FAKE_TXHASH_9ac7d2),
                    request_output(1, FAKE_TXHASH_9ac7d2),
                    request_input(1),
                    request_meta(FAKE_TXHASH_48f5b8),
                    request_input(0, FAKE_TXHASH_48f5b8),
                    request_output(0, FAKE_TXHASH_48f5b8),
                    request_output(1, FAKE_TXHASH_48f5b8),
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
        == "0100000002d18f50c5e465b727fee4af645350093a8baf7e04ee8ef34ecf0c46f422d2c79a0100000000fffffffff32d5470c1a96b2d9d5215066bd2e254f191d4ce8873d0d096f71c8b5fb8f5480000000000ffffffff02605af40500000000000017a914d4ea4e064d969064ca56a4cede56f7bf6cf62f118700a3e1110000000000001976a9143eb656115197956125365348c542e37b6d3d259988ac00000000000000000200c2eb0b0000000000000000fffffffffc483045022100e7056e4cbc0941a1255e85ab95634fd9ae497be9a8ab0e793d6049f7dd97fa07022031c17d6279211843ea1e0815a1831748aa44c3a3083669293805f8e9e803d78d01473044022039b74918f67afd24f20c0bf4d0ea40637d85005bbb942e7c79e17694e4729e0902202563fa43376220261bb177fc87d637d39809e0ffa4991a1477dbc60a1c2e3997014c69522103defea6f243b97354449bb348446a97e38df2fbed33afc3a7185bfdd26757cfdb2103725d6c5253f2040a9a73af24bcc196bf302d6cc94374dd7197b138e10912670121038924e94fff15302a3fb45ad4fc0ed17178800f0f1c2bdacb1017f4db951aa9f153ae00c2eb0b0000000000000000fffffffffb473044022047afb55f956ef7ac7d4a32e97fe35b3981cd827866ccd76e66b7f186a5338f9302201415cdd987876e8c6c13037e53d055aac467acece41d9357657e4fd8290d914101473044022005cb0efd5889d697e040b2db5d56ef7e1d29fcd20b74a8cc44d670092b6cfaee02202150837c1f5108af8b6cc022bd2d40e54170869ad39b2d1d61c67a47ad21e019014c695221021ef4b5d81f21593071b993bd4d8c564c569a6f84de0d4511135cbc66d8bf7bcd2103f1e53b6e0ff99adf7e8fa826a94bdac83163d8abbc1d19a8d6b88a4af91b9a67210390c8ea70e1f2f60e0052be65183c43bb01b2f02dfa4e448f74e359997f74e6ad53ae"
    )
