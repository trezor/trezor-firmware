# This file is part of the Trezor project.
#
# Copyright (C) 2020 SatoshiLabs and contributors
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
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..tx_cache import TxCache
from .signtx import (
    request_finished,
    request_input,
    request_meta,
    request_orig_input,
    request_orig_output,
    request_output,
)

B = messages.ButtonRequestType

TX_CACHE_TESTNET = TxCache("Testnet")
TX_CACHE_MAINNET = TxCache("Bitcoin")

TXHASH_50f6f1 = bytes.fromhex(
    "50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d"
)
TXHASH_beafc7 = bytes.fromhex(
    "beafc7cbd873d06dbee88a7002768ad5864228639db514c81cfb29f108bb1e7a"
)
TXHASH_65b768 = bytes.fromhex(
    "65b768dacccfb209eebd95a1fb80a04f1dd6a3abc6d7b41d5e9d9f91605b37d9"
)
TXHASH_e4b5b2 = bytes.fromhex(
    "e4b5b24159856ea18ab5819832da3b4a6330f9c3c0a46d96674e632df504b56b"
)
TXHASH_70f987 = bytes.fromhex(
    "70f9871eb03a38405cfd7a01e0e1448678132d815e2c9f552ad83ae23969509e"
)
TXHASH_334cd7 = bytes.fromhex(
    "334cd7ad982b3b15d07dd1c84e939e95efb0803071648048a7f289492e7b4c8a"
)
TXHASH_5e7667 = bytes.fromhex(
    "5e7667690076ae4737e2f872005de6f6b57592f32108ed9b301eeece6de24ad6"
)
TXHASH_efaa41 = bytes.fromhex(
    "efaa41ff3e67edf508846c1a1ed56894cfd32725c590300108f40c9edc1aac35"
)
TXHASH_ed89ac = bytes.fromhex(
    "ed89acb52cfa438e3653007478e7c7feae89fdde12867943eec91293139730d1"
)
TXHASH_6673b7 = bytes.fromhex(
    "6673b7248e324882b2f9d02fdd1ff1d0f9ed216a234e836b8d3ac65661cbb457"
)
TXHASH_927784 = bytes.fromhex(
    "927784e07bbcefc4c738f5c31c7a739978fc86f35514edf7e7da25d53d83030b"
)
TXHASH_43d273 = bytes.fromhex(
    "43d273d3caf41759ad843474f960fbf80ff2ec961135d018b61e9fab3ad1fc06"
)
TXHASH_408397 = bytes.fromhex(
    "4083973799f05c52f556b603ab0f93d9c4c50be50da03c770a492d0990ca7809"
)
TXHASH_ba917a = bytes.fromhex(
    "ba917a2b563966e324ab37ed7de5f5cd7503b970b0f0bb9a5208f5835557e99c"
)


def test_p2pkh_fee_bump(client):
    inp1 = messages.TxInputType(
        address_n=parse_path("44h/0h/0h/0/4"),
        amount=174998,
        prev_hash=TXHASH_beafc7,
        prev_index=0,
        orig_hash=TXHASH_50f6f1,
        orig_index=0,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("44h/0h/0h/1/2"),
        amount=174998 - 50000 - 15000,  # Originally fee was 11300, now 15000.
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        orig_hash=TXHASH_50f6f1,
        orig_index=0,
    )

    out2 = messages.TxOutputType(
        address="1GA9u9TfCG7SWmKCveBumdA1TZpfom6ZdJ",
        amount=50000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        orig_hash=TXHASH_50f6f1,
        orig_index=1,
    )

    tt = client.features.model == "T"

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_meta(TXHASH_50f6f1),
                request_orig_input(0, TXHASH_50f6f1),
                messages.ButtonRequest(code=B.SignTx),
                request_output(0),
                request_orig_output(0, TXHASH_50f6f1),
                request_output(1),
                request_orig_output(1, TXHASH_50f6f1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_beafc7),
                request_input(0, TXHASH_beafc7),
                request_output(0, TXHASH_beafc7),
                (tt, request_orig_input(0, TXHASH_50f6f1)),
                (tt, request_orig_output(0, TXHASH_50f6f1)),
                (tt, request_orig_output(1, TXHASH_50f6f1)),
                request_input(0),
                request_output(0),
                request_output(1),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Bitcoin",
            [inp1],
            [out1, out2],
            prev_txes=TX_CACHE_MAINNET,
        )

    assert (
        serialized_tx.hex()
        == "01000000017a1ebb08f129fb1cc814b59d63284286d58a7602708ae8be6dd073d8cbc7afbe000000006b483045022100a8c1c118d61259f8df463deb538a10d9e9f42bbdfff28bb1337ee5426e5098f8022060e7464f7a63a83fd93dbd268f319133cb03452764afd601db063ff3eede9207012103f54094da6a0b2e0799286268bb59ca7c83538e81c78e64f6333f40f9e0e222c0ffffffff02aead0100000000001976a914902c642ba3a22f5c6cfa30a1790c133ddf15cc8888ac50c30000000000001976a914a6450f1945831a81912616691e721b787383f4ed88ac00000000"
    )


def test_p2wpkh_op_return_fee_bump(client):
    # Original input.
    inp1 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/1h/0/14"),
        amount=1000000,
        script_type=messages.InputScriptType.SPENDWITNESS,
        prev_hash=TXHASH_408397,
        prev_index=1,
        orig_hash=TXHASH_ba917a,
        orig_index=0,
        sequence=4294967293,
    )

    # Original OP_RETURN output.
    out1 = messages.TxOutputType(
        amount=0,
        op_return_data=b"dead",
        script_type=messages.OutputScriptType.PAYTOOPRETURN,
        orig_hash=TXHASH_ba917a,
        orig_index=0,
    )

    # Change-output. We bump the fee from 150 to 300.
    out2 = messages.TxOutputType(
        address_n=parse_path("m/84h/1h/1h/1/10"),
        amount=999850 - 150,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
        orig_hash=TXHASH_ba917a,
        orig_index=1,
    )

    with client:
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1],
            [out1, out2],
            prev_txes=TX_CACHE_TESTNET,
        )

    assert (
        serialized_tx.hex()
        == "010000000001010978ca90092d490a773ca00de50bc5c4d9930fab03b656f5525cf099379783400100000000fdffffff020000000000000000066a046465616414410f00000000001600141c02e2397a8a02ff71d3f26937d14a656469dd1f02483045022100f534412752c14064470d4a1f738fa01bc83598b07caaba4cd207b43b1b9702a4022071a4f0873006c07ccfeb1f82e86f3047eab208f38cfa41d7b566d6ca50dbca0f012102a269d4b8faf008074b974b6d64fa1776e17fdf65381a76d1338e9bba88983a8700000000"
    )


def test_p2wpkh_finalize(client):
    # Original input with disabled RBF opt-in, i.e. we finalize the transaction.
    inp1 = messages.TxInputType(
        address_n=parse_path("84h/1h/0h/0/2"),
        amount=20000000,
        script_type=messages.InputScriptType.SPENDWITNESS,
        prev_hash=TXHASH_43d273,
        prev_index=1,
        orig_hash=TXHASH_70f987,
        orig_index=0,
        sequence=4294967294,
    )

    # Original external output (actually 84h/1h/0h/0/0).
    out1 = messages.TxOutputType(
        address="tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9",
        amount=100000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
        orig_hash=TXHASH_70f987,
        orig_index=0,
    )

    # Change output. We bump the fee from 141 to 200.
    out2 = messages.TxOutputType(
        address_n=parse_path("84h/1h/0h/1/1"),
        amount=20000000 - 100000 - 200,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
        orig_hash=TXHASH_70f987,
        orig_index=1,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_meta(TXHASH_70f987),
                request_orig_input(0, TXHASH_70f987),
                messages.ButtonRequest(code=B.SignTx),
                request_output(0),
                request_orig_output(0, TXHASH_70f987),
                request_output(1),
                request_orig_output(1, TXHASH_70f987),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_43d273),
                request_input(0, TXHASH_43d273),
                request_output(0, TXHASH_43d273),
                request_output(1, TXHASH_43d273),
                request_output(2, TXHASH_43d273),
                request_input(0),
                request_output(0),
                request_output(1),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1],
            [out1, out2],
            lock_time=1348713,
            prev_txes=TX_CACHE_TESTNET,
        )

    assert (
        serialized_tx.hex()
        == "0100000000010106fcd13aab9f1eb618d0351196ecf20ff8fb60f9743484ad5917f4cad373d2430100000000feffffff02a086010000000000160014b31dc2a236505a6cb9201fa0411ca38a254a7bf198a52f0100000000160014167dae080bca35c9ea49c0c8335dcc4b252a1d700247304402201ee1828ab0ca7f8113989399edda8394c65e5c3c9fe597a78890c5d2c9bd2aeb022010e76ad6abe171e5cded6b374a344ee18a51d38477b76a4b6fb30289ed24beff01210357cb3a5918d15d224f14a89f0eb54478272108f6cbb9c473c1565e55260f6e9369941400"
    )


@pytest.mark.skip_t1
@pytest.mark.parametrize(
    "out1_amount, out2_amount, copayer_witness, fee_confirm, expected_tx",
    (
        (
            # Scenario 1: No fee bump by sender or receiver.
            10000 + 19899859,  # out1: Receiver does not contribute to fee.
            100000 - 10000 - 141,  # out2: Original change.
            "02483045022100eb74abb36f317d707c36d6fe1f4f73192d54417b9d5cd274e0077590833aad0a02206cf26621706aaf232c48a139910de71f7dbf17f3fb6af52a7222d19d88041e8b012102d587bc96e0ceab05f27401d66dc3e596ba02f2c0d7b018b5f80eebfaeb011012",
            False,
            "010000000001026bb504f52d634e67966da4c0c3f930634a3bda329881b58aa16e855941b2b5e400000000005a2417009e506939e23ad82a559f2c5e812d13788644e1e0017afd5c40383ab01e87f9700100000000ffffffff02e3cc2f0100000000160014fb7e49f4017dc951615dea221b66626189aa43b9035f0100000000001600141d03a4d2167961b853d6cadfeab08e4937c5dfe802483045022100fd695bb0b5d07f0578ba56cb385b7662b98a1eb7d61ac25eaa565376ebd042de02201dc5209206d5d4c1bb79f9278a330767bf73afa774cd6a8331068d430bc95e50012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86202483045022100eb74abb36f317d707c36d6fe1f4f73192d54417b9d5cd274e0077590833aad0a02206cf26621706aaf232c48a139910de71f7dbf17f3fb6af52a7222d19d88041e8b012102d587bc96e0ceab05f27401d66dc3e596ba02f2c0d7b018b5f80eebfaeb0110125a241700",
        ),
        (
            # Scenario 2: Sender fee bump only.
            10000 + 19899859,  # out1: Receiver does not contribute to fee.
            100000 - 10000 - 200,  # out2: Sender bumps fee from 141 to 200.
            "02483045022100af3a874c966ee595321e8699e7157f0b21f2542ddcdcafd06a9c2b4fd75e998b02206daecf235b5eb3c9dac088c904774cc0a61ac601c840efc5cbe00f99e1979a09012102d587bc96e0ceab05f27401d66dc3e596ba02f2c0d7b018b5f80eebfaeb011012",
            True,
            "010000000001026bb504f52d634e67966da4c0c3f930634a3bda329881b58aa16e855941b2b5e400000000005a2417009e506939e23ad82a559f2c5e812d13788644e1e0017afd5c40383ab01e87f9700100000000ffffffff02e3cc2f0100000000160014fb7e49f4017dc951615dea221b66626189aa43b9c85e0100000000001600141d03a4d2167961b853d6cadfeab08e4937c5dfe8024730440220524e0f020a4ed910fa8e654feca8a2d54962e9691b2e1be9648685fbe84d900402203971dbba53400ed93d69dc5811cc0c7b3d368ffa9ba92c746fda8925bd5f556f012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86202483045022100af3a874c966ee595321e8699e7157f0b21f2542ddcdcafd06a9c2b4fd75e998b02206daecf235b5eb3c9dac088c904774cc0a61ac601c840efc5cbe00f99e1979a09012102d587bc96e0ceab05f27401d66dc3e596ba02f2c0d7b018b5f80eebfaeb0110125a241700",
        ),
        (
            # Scenario 3: Receiver fee bump.
            10000 + 19899859 - 59,  # out1: Receiver contributes 59 to fee.
            100000 - 10000 - 141,  # out2: Sender does not bump fee.
            "0248304502210097a42b35d3d16fa169667cd85a007eaf6b674495634b120d9fb62d72a0df872402203d0cdf746fd7a668276f93f660a9d052bc8a5d7cd8fea36073de38da463ece85012102d587bc96e0ceab05f27401d66dc3e596ba02f2c0d7b018b5f80eebfaeb011012",
            False,
            "010000000001026bb504f52d634e67966da4c0c3f930634a3bda329881b58aa16e855941b2b5e400000000005a2417009e506939e23ad82a559f2c5e812d13788644e1e0017afd5c40383ab01e87f9700100000000ffffffff02a8cc2f0100000000160014fb7e49f4017dc951615dea221b66626189aa43b9035f0100000000001600141d03a4d2167961b853d6cadfeab08e4937c5dfe802473044022002bdb052c49648cd7a9488080c5489f89cff52b752acfcabf6e130d2e9f9fe3902202433f50b8b2a0cc4d463c44c0f24812e0b7f2f5c8f2ec67137694a934335b60f012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f8620248304502210097a42b35d3d16fa169667cd85a007eaf6b674495634b120d9fb62d72a0df872402203d0cdf746fd7a668276f93f660a9d052bc8a5d7cd8fea36073de38da463ece85012102d587bc96e0ceab05f27401d66dc3e596ba02f2c0d7b018b5f80eebfaeb0110125a241700",
        ),
        (
            # Scenario 4: Receiver pays entire fee.
            10000 + 19899859 - 141,  # out1: Receiver pays entire original fee of 141.
            100000 - 10000,  # out2: Sender pays no fee.
            "024730440220753f53049ca43d55f65633d3f1a8fe0464f24f780070db27474fd48d161b958302204a08e2956ac9bf1bdc762eb19f77cab5aa22ab24e058f31b8db2b878c875be74012102d587bc96e0ceab05f27401d66dc3e596ba02f2c0d7b018b5f80eebfaeb011012",
            False,
            "010000000001026bb504f52d634e67966da4c0c3f930634a3bda329881b58aa16e855941b2b5e400000000005a2417009e506939e23ad82a559f2c5e812d13788644e1e0017afd5c40383ab01e87f9700100000000ffffffff0256cc2f0100000000160014fb7e49f4017dc951615dea221b66626189aa43b9905f0100000000001600141d03a4d2167961b853d6cadfeab08e4937c5dfe802483045022100e7f8b2d226cf98ab342c99d1bd51728661c8a81c94b0e198ea423c3cf704c29402203f522364bd1e4221bd5aa2db2364f1618b67fcddf54a838d8994b9f51f0c1c0c012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f862024730440220753f53049ca43d55f65633d3f1a8fe0464f24f780070db27474fd48d161b958302204a08e2956ac9bf1bdc762eb19f77cab5aa22ab24e058f31b8db2b878c875be74012102d587bc96e0ceab05f27401d66dc3e596ba02f2c0d7b018b5f80eebfaeb0110125a241700",
        ),
        (
            # Scenario 5: Receiver bumps and pays entire fee.
            10000 + 19899859 - 200,  # out1: Receiver bumps fee from 141 to 200.
            100000 - 10000,  # out2: Sender pays no fee.
            "02483045022100aa1b91fb25cc9a0ace45db3dfae5d0beffdda4b76ccd4f362b460729efdf78b502206ed6de7fb6cdacdddd90f184416a46ea692f4a656a26702665bf2db1ef080a03012102d587bc96e0ceab05f27401d66dc3e596ba02f2c0d7b018b5f80eebfaeb011012",
            False,
            "010000000001026bb504f52d634e67966da4c0c3f930634a3bda329881b58aa16e855941b2b5e400000000005a2417009e506939e23ad82a559f2c5e812d13788644e1e0017afd5c40383ab01e87f9700100000000ffffffff021bcc2f0100000000160014fb7e49f4017dc951615dea221b66626189aa43b9905f0100000000001600141d03a4d2167961b853d6cadfeab08e4937c5dfe802473044022075c504c90351394d0d019bc5022f860ecb33c0fcbf3b448b97d03169d1605427022007f0330591652a9a4a36417dc1477c8242abcc5110b312dfffc04df06901979c012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86202483045022100aa1b91fb25cc9a0ace45db3dfae5d0beffdda4b76ccd4f362b460729efdf78b502206ed6de7fb6cdacdddd90f184416a46ea692f4a656a26702665bf2db1ef080a03012102d587bc96e0ceab05f27401d66dc3e596ba02f2c0d7b018b5f80eebfaeb0110125a241700",
        ),
    ),
)
def test_p2wpkh_payjoin(
    client, out1_amount, out2_amount, copayer_witness, fee_confirm, expected_tx
):
    # Original input.
    inp1 = messages.TxInputType(
        address_n=parse_path("84h/1h/0h/0/0"),
        amount=100000,
        script_type=messages.InputScriptType.SPENDWITNESS,
        prev_hash=TXHASH_e4b5b2,
        prev_index=0,
        orig_hash=TXHASH_65b768,
        orig_index=0,
        sequence=1516634,
    )

    # New presigned external input. (Actually 84h/1h/0h/1/1, making it easier to generate witnesses.)
    inp2 = messages.TxInputType(
        amount=19899859,
        script_type=messages.InputScriptType.EXTERNAL,
        prev_hash=TXHASH_70f987,
        prev_index=1,
        script_pubkey=bytes.fromhex("0014167dae080bca35c9ea49c0c8335dcc4b252a1d70"),
        witness=bytes.fromhex(copayer_witness),
    )

    # PayJoined output.
    out1 = messages.TxOutputType(
        address="tb1qldlynaqp0hy4zc2aag3pkenzvxy65saesxw3wd",
        # Originally payment was 10000, now we add receiver's inp2.
        amount=out1_amount,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
        orig_hash=TXHASH_65b768,
        orig_index=0,
    )

    # Original change.
    out2 = messages.TxOutputType(
        address_n=parse_path("84h/1h/0h/1/2"),
        amount=out2_amount,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
        orig_hash=TXHASH_65b768,
        orig_index=1,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_meta(TXHASH_65b768),
                request_orig_input(0, TXHASH_65b768),
                request_input(1),
                messages.ButtonRequest(code=B.SignTx),
                request_output(0),
                request_orig_output(0, TXHASH_65b768),
                request_output(1),
                request_orig_output(1, TXHASH_65b768),
                (fee_confirm, messages.ButtonRequest(code=B.SignTx)),
                request_input(0),
                request_meta(TXHASH_e4b5b2),
                request_input(0, TXHASH_e4b5b2),
                request_output(0, TXHASH_e4b5b2),
                request_output(1, TXHASH_e4b5b2),
                request_input(1),
                request_meta(TXHASH_70f987),
                request_input(0, TXHASH_70f987),
                request_output(0, TXHASH_70f987),
                request_output(1, TXHASH_70f987),
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                request_input(0),
                request_input(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1, out2],
            lock_time=1516634,
            prev_txes=TX_CACHE_TESTNET,
        )

    assert serialized_tx.hex() == expected_tx


def test_p2wpkh_in_p2sh_remove_change(client):
    # Test fee bump with change-output removal. Originally fee was 3780, now 98060.

    inp1 = messages.TxInputType(
        address_n=parse_path("49h/1h/0h/0/4"),
        amount=100000,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        prev_hash=TXHASH_5e7667,
        prev_index=1,
        orig_hash=TXHASH_334cd7,
        orig_index=0,
    )

    inp2 = messages.TxInputType(
        address_n=parse_path("49h/1h/0h/0/3"),
        amount=998060,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        prev_hash=TXHASH_efaa41,
        prev_index=0,
        orig_hash=TXHASH_334cd7,
        orig_index=1,
    )

    out1 = messages.TxOutputType(
        # Actually m/49'/1'/0'/0/5.
        address="2MvUUSiQZDSqyeSdofKX9KrSCio1nANPDTe",
        amount=1000000,
        orig_hash=TXHASH_334cd7,
        orig_index=0,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_meta(TXHASH_334cd7),
                request_orig_input(0, TXHASH_334cd7),
                request_input(1),
                request_orig_input(1, TXHASH_334cd7),
                messages.ButtonRequest(code=B.SignTx),
                request_output(0),
                request_orig_output(0, TXHASH_334cd7),
                request_orig_output(1, TXHASH_334cd7),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_5e7667),
                request_input(0, TXHASH_5e7667),
                request_output(0, TXHASH_5e7667),
                request_output(1, TXHASH_5e7667),
                request_input(1),
                request_meta(TXHASH_efaa41),
                request_input(0, TXHASH_efaa41),
                request_output(0, TXHASH_efaa41),
                request_input(0),
                request_input(1),
                request_output(0),
                request_input(0),
                request_input(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1],
            prev_txes=TX_CACHE_TESTNET,
        )

    assert (
        serialized_tx.hex()
        == "01000000000102d64ae26dceee1e309bed0821f39275b5f6e65d0072f8e23747ae76006967765e0100000017160014039ba06270e6c6c1ad4e6940515aa5cdbad33f9effffffff35ac1adc9e0cf408013090c52527d3cf9468d51e1a6c8408f5ed673eff41aaef0000000017160014209297fb46272a0b7e05139440dbd39daea3e25affffffff0140420f000000000017a9142369da13fee80c9d7fd8043bf1275c04deb360e68702483045022100c28eceaade3d0bc82e4b634d2c6d06feed4afe37c77b04b379eaf8c058b7190702202b7a369dd6104c13c60821c1ad4e7c2d8d37cf1962a9b3f5d70717709c021d63012103bb0e339d7495b1f355c49d385b79343e52e68d99de2fe1f7f476c465c9ccd16702483045022100f6a447b7f95fb067c87453c408aa648262adaf2472a7ccc754518cd06353b87502202e00359dd663eda24d381e070b92a5e41f1d047d276f685ff549a03659842b1b012103c2c2e65556ca4b7371549324b99390725493c8a6792e093a0bdcbb3e2d7df4ab00000000"
    )


def test_p2wpkh_in_p2sh_fee_bump_from_external(client):
    # Use the change output and an external output to bump the fee.
    # Originally fee was 3780, now 108060 (94280 from change and 10000 from external).

    inp1 = messages.TxInputType(
        address_n=parse_path("49h/1h/0h/0/4"),
        amount=100000,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        prev_hash=TXHASH_5e7667,
        prev_index=1,
        orig_hash=TXHASH_334cd7,
        orig_index=0,
    )

    inp2 = messages.TxInputType(
        address_n=parse_path("49h/1h/0h/0/3"),
        amount=998060,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        prev_hash=TXHASH_efaa41,
        prev_index=0,
        orig_hash=TXHASH_334cd7,
        orig_index=1,
    )

    out1 = messages.TxOutputType(
        # Actually m/49'/1'/0'/0/5.
        address="2MvUUSiQZDSqyeSdofKX9KrSCio1nANPDTe",
        amount=990000,
        orig_hash=TXHASH_334cd7,
        orig_index=0,
    )

    t1 = client.features.model == "1"
    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_meta(TXHASH_334cd7),
                request_orig_input(0, TXHASH_334cd7),
                request_input(1),
                request_orig_input(1, TXHASH_334cd7),
                messages.ButtonRequest(code=B.SignTx),
                request_output(0),
                request_orig_output(0, TXHASH_334cd7),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (t1, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_orig_output(1, TXHASH_334cd7),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_5e7667),
                request_input(0, TXHASH_5e7667),
                request_output(0, TXHASH_5e7667),
                request_output(1, TXHASH_5e7667),
                request_input(1),
                request_meta(TXHASH_efaa41),
                request_input(0, TXHASH_efaa41),
                request_output(0, TXHASH_efaa41),
                request_input(0),
                request_input(1),
                request_output(0),
                request_input(0),
                request_input(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1],
            prev_txes=TX_CACHE_TESTNET,
        )

    assert (
        serialized_tx.hex()
        == "01000000000102d64ae26dceee1e309bed0821f39275b5f6e65d0072f8e23747ae76006967765e0100000017160014039ba06270e6c6c1ad4e6940515aa5cdbad33f9effffffff35ac1adc9e0cf408013090c52527d3cf9468d51e1a6c8408f5ed673eff41aaef0000000017160014209297fb46272a0b7e05139440dbd39daea3e25affffffff01301b0f000000000017a9142369da13fee80c9d7fd8043bf1275c04deb360e68702483045022100bd303aa0d923e73300e37971d43b9cd134230f8287e0e3b702aacd19ba8ef97b02202b4368b3e9d7478b8529ea2aeea23f6612ec05854510794958d6ce58c19082ad012103bb0e339d7495b1f355c49d385b79343e52e68d99de2fe1f7f476c465c9ccd1670247304402204869b27aa926d98bfd36912f71e335c1d6afb2c1a28102407066db5257e1b8810220197bcac3c85a721547974bd7309a6ea2b809810a595cbdca2da9599af4038ba2012103c2c2e65556ca4b7371549324b99390725493c8a6792e093a0bdcbb3e2d7df4ab00000000"
    )


@pytest.mark.skip_t1
def test_tx_meld(client):
    # Meld two original transactions into one, joining the change-outputs into a different one.

    inp1 = messages.TxInputType(
        address_n=parse_path("49h/1h/0h/0/4"),
        amount=100000,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        prev_hash=TXHASH_5e7667,
        prev_index=1,
        orig_hash=TXHASH_334cd7,
        orig_index=0,
    )

    inp2 = messages.TxInputType(
        address_n=parse_path("49h/1h/0h/0/8"),
        amount=4973340,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        prev_hash=TXHASH_6673b7,
        prev_index=0,
        orig_hash=TXHASH_ed89ac,
        orig_index=0,
    )

    inp3 = messages.TxInputType(
        address_n=parse_path("49h/1h/0h/0/3"),
        amount=998060,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        prev_hash=TXHASH_efaa41,
        prev_index=0,
        orig_hash=TXHASH_334cd7,
        orig_index=1,
    )

    inp4 = messages.TxInputType(
        address_n=parse_path("49h/1h/0h/0/9"),
        amount=839318869,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        prev_hash=TXHASH_927784,
        prev_index=0,
        orig_hash=TXHASH_ed89ac,
        orig_index=1,
    )

    out1 = messages.TxOutputType(
        address="moE1dVYvebvtaMuNdXQKvu4UxUftLmS1Gt",
        amount=100000000,
        orig_hash=TXHASH_ed89ac,
        orig_index=1,
    )

    out2 = messages.TxOutputType(
        # Actually m/49'/1'/0'/0/5.
        address="2MvUUSiQZDSqyeSdofKX9KrSCio1nANPDTe",
        amount=1000000,
        orig_hash=TXHASH_334cd7,
        orig_index=0,
    )

    # Change-output. Original fees were 3780 + 90720 = 94500.
    out3 = messages.TxOutputType(
        address_n=parse_path("49h/1h/0h/1/0"),
        amount=100000 + 4973340 + 998060 + 839318869 - 100000000 - 1000000 - 94500,
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_meta(TXHASH_334cd7),
                request_orig_input(0, TXHASH_334cd7),
                request_input(1),
                request_meta(TXHASH_ed89ac),
                request_orig_input(0, TXHASH_ed89ac),
                request_input(2),
                request_orig_input(1, TXHASH_334cd7),
                request_input(3),
                request_orig_input(1, TXHASH_ed89ac),
                messages.ButtonRequest(code=B.SignTx),
                messages.ButtonRequest(code=B.SignTx),
                request_output(0),
                request_orig_output(0, TXHASH_ed89ac),
                request_orig_output(1, TXHASH_ed89ac),
                request_output(1),
                request_orig_output(0, TXHASH_334cd7),
                request_output(2),
                request_orig_output(1, TXHASH_334cd7),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_5e7667),
                request_input(0, TXHASH_5e7667),
                request_output(0, TXHASH_5e7667),
                request_output(1, TXHASH_5e7667),
                request_input(1),
                request_meta(TXHASH_6673b7),
                request_input(0, TXHASH_6673b7),
                request_input(1, TXHASH_6673b7),
                request_input(2, TXHASH_6673b7),
                request_input(3, TXHASH_6673b7),
                request_input(4, TXHASH_6673b7),
                request_output(0, TXHASH_6673b7),
                request_input(2),
                request_meta(TXHASH_efaa41),
                request_input(0, TXHASH_efaa41),
                request_output(0, TXHASH_efaa41),
                request_input(3),
                request_meta(TXHASH_927784),
                request_input(0, TXHASH_927784),
                request_input(1, TXHASH_927784),
                request_input(2, TXHASH_927784),
                request_output(0, TXHASH_927784),
                request_input(0),
                request_input(1),
                request_input(2),
                request_input(3),
                request_output(0),
                request_output(1),
                request_output(2),
                request_input(0),
                request_input(1),
                request_input(2),
                request_input(3),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2, inp3, inp4],
            [out1, out2, out3],
            prev_txes=TX_CACHE_TESTNET,
        )

    assert (
        serialized_tx.hex()
        == "01000000000104d64ae26dceee1e309bed0821f39275b5f6e65d0072f8e23747ae76006967765e0100000017160014039ba06270e6c6c1ad4e6940515aa5cdbad33f9effffffff57b4cb6156c63a8d6b834e236a21edf9d0f11fdd2fd0f9b28248328e24b773660000000017160014adbbadefe594e9e4bfccb9c699ae5d4f18716772ffffffff35ac1adc9e0cf408013090c52527d3cf9468d51e1a6c8408f5ed673eff41aaef0000000017160014209297fb46272a0b7e05139440dbd39daea3e25affffffff0b03833dd525dae7f7ed1455f386fc7899737a1cc3f538c7c4efbc7be08477920000000017160014681ea49259abb892460bf3373e8a0b43d877fa18ffffffff0300e1f505000000001976a914548cb80e45b1d36312fe0cb075e5e337e3c54cef88ac40420f000000000017a9142369da13fee80c9d7fd8043bf1275c04deb360e687590d5d2c0000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca870247304402205b4b304cb5a23cd3b73aa586c983cbadefc3fcbcb8fb33684037b17a818726c002202a3f529183eebf2f06d041b18d379579c22d908be31060752179f01d125ff020012103bb0e339d7495b1f355c49d385b79343e52e68d99de2fe1f7f476c465c9ccd167024730440220666ebf2c146d4a369971ec1d5b69fce2f3b8e2c0ba689e6077ebed513f91dd760220200e203355156e23abf5b536ac174df4109985feddf86ab065c12f0da8339d6a012102a52d8cf5a89c284bacff90a3d7c30a0166e0074ca3fc385f3efce638c50493b30247304402207d6331026626fc133813ea672147c95feac29a3d7deefb49ef1d0194e061d53802207e4c3a3b8f3c2e11845684d74a5f1d8395da0a8e65e18c7f72155aac82be648e012103c2c2e65556ca4b7371549324b99390725493c8a6792e093a0bdcbb3e2d7df4ab02473044022047f95a95ea8cac78f057e15e37ac5cebd6abcf50d87e5509d30c730cb0f7e89f02201d861acb267c0bc100cac99cad42b067a39614602eef5f9f791c1875f24dd0de0121028cbc37e1816a23086fa738c8415def477e813e20f484dbbd6f5a33a37c32225100000000"
    )


def test_attack_steal_change(client):
    # Attempt to steal amount equivalent to the change in the original transaction by
    # hiding the fact that an output in the original transaction is a change-output.

    # Original input.
    inp1 = messages.TxInputType(
        address_n=parse_path("84h/1h/0h/0/0"),
        amount=100000,
        script_type=messages.InputScriptType.SPENDWITNESS,
        prev_hash=TXHASH_e4b5b2,
        prev_index=0,
        orig_hash=TXHASH_65b768,
        orig_index=0,
        sequence=1516634,
    )

    # New input for the attacker to steal from.
    inp2 = messages.TxInputType(
        address_n=parse_path("84h/1h/0h/1/1"),
        amount=19899859,
        script_type=messages.InputScriptType.SPENDWITNESS,
        prev_hash=TXHASH_70f987,
        prev_index=1,
    )

    # Original output.
    out1 = messages.TxOutputType(
        address="tb1qldlynaqp0hy4zc2aag3pkenzvxy65saesxw3wd",
        amount=10000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
        orig_hash=TXHASH_65b768,
        orig_index=0,
    )

    # Original change was 89859. We bump the fee from 141 to 200 and
    # attacker gives back what he can't steal.
    out2 = messages.TxOutputType(
        address_n=parse_path("84h/1h/0h/1/2"),
        amount=100000 - 10000 - 200 + (19899859 - 89859),
        script_type=messages.OutputScriptType.PAYTOWITNESS,
        orig_hash=TXHASH_65b768,
        orig_index=1,
    )

    # Attacker's new output.
    out3 = messages.TxOutputType(
        address="tb1q694ccp5qcc0udmfwgp692u2s2hjpq5h407urtu",
        amount=89859,
    )

    # Attacker hides the fact that second output of 65b768 is a change-output.
    prev_tx_attack = TX_CACHE_TESTNET[TXHASH_65b768]
    prev_tx_attack.outputs[1].address_n = None
    prev_tx_attack.outputs[1].address = "tb1qr5p6f5sk09sms57ket074vywfymuthlgud7xyx"
    prev_tx_attack.outputs[1].script_type = messages.OutputScriptType.PAYTOADDRESS
    prev_txes = {TXHASH_65b768: prev_tx_attack}

    with pytest.raises(
        TrezorFailure, match="Original output is missing change-output parameters"
    ):
        btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1, out2, out3],
            lock_time=1516634,
            prev_txes=prev_txes,
        )


@pytest.mark.skip_t1
def test_attack_false_internal(client):
    # Falsely claim that an external input is internal in the original transaction.
    # If this were possible, it would allow an attacker to make it look like the
    # user was spending more in the original than they actually were, making it
    # possible for the attacker to steal the difference.

    inp1 = messages.TxInputType(
        address_n=parse_path("49h/1h/0h/0/4"),
        amount=100000,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        prev_hash=TXHASH_5e7667,
        prev_index=1,
        orig_hash=TXHASH_334cd7,
        orig_index=0,
    )

    inp2 = messages.TxInputType(
        # Actually 49h/1h/0h/0/3, but we will make it look like it's external,
        # while in the original it will show up as intenal.
        amount=998060,
        script_type=messages.InputScriptType.EXTERNAL,
        prev_hash=TXHASH_efaa41,
        prev_index=0,
        orig_hash=TXHASH_334cd7,
        orig_index=1,
        script_pubkey=bytes.fromhex("a914b9170a062fafcf4379729d104dd04859b1ce955887"),
        script_sig=bytes.fromhex("160014209297fb46272a0b7e05139440dbd39daea3e25a"),
        witness=bytes.fromhex(
            "024730440220709798e66e44ee76d8b0858407b2098f2f0046703761e2617b2b870a346cb56c022010242f602cd41485934834ecf12c1647d003df8c9d4c0d8637514e1dc8a657a2012103c2c2e65556ca4b7371549324b99390725493c8a6792e093a0bdcbb3e2d7df4ab"
        ),
    )

    out1 = messages.TxOutputType(
        # Actually m/49'/1'/0'/0/5.
        address="2MvUUSiQZDSqyeSdofKX9KrSCio1nANPDTe",
        amount=1000000 + 94280,
        orig_hash=TXHASH_334cd7,
        orig_index=0,
    )

    with pytest.raises(
        TrezorFailure, match="Original input does not match current input"
    ):
        btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1],
            prev_txes=TX_CACHE_TESTNET,
        )


def test_attack_fake_int_input_amount(client):
    # Give a fake input amount for an original internal input while giving the correct
    # amount for the replacement input. If an attacker could increase the amount of an
    # internal input in the original transaction, then they could bump the fee of the
    # transaction without the user noticing.

    inp1 = messages.TxInputType(
        address_n=parse_path("44h/0h/0h/0/4"),
        amount=174998,
        prev_hash=TXHASH_beafc7,
        prev_index=0,
        orig_hash=TXHASH_50f6f1,
        orig_index=0,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("44h/0h/0h/1/2"),
        amount=174998
        - 50000
        - 111300,  # Original fee was 11300, attacker increases it by 100000.
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        orig_hash=TXHASH_50f6f1,
        orig_index=0,
    )

    out2 = messages.TxOutputType(
        address="1GA9u9TfCG7SWmKCveBumdA1TZpfom6ZdJ",
        amount=50000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        orig_hash=TXHASH_50f6f1,
        orig_index=1,
    )

    prev_tx_attack = TX_CACHE_MAINNET[TXHASH_50f6f1]
    prev_tx_attack.inputs[
        0
    ].amount += 100000  # Increase the original input amount by 100000.
    prev_txes = {
        TXHASH_50f6f1: prev_tx_attack,
        TXHASH_beafc7: TX_CACHE_MAINNET[TXHASH_beafc7],
    }

    with pytest.raises(
        TrezorFailure, match="Original input does not match current input"
    ):
        btc.sign_tx(
            client,
            "Bitcoin",
            [inp1],
            [out1, out2],
            prev_txes=prev_txes,
        )


@pytest.mark.skip_t1
def test_attack_fake_ext_input_amount(client):
    # Give a fake input amount for an original external input while giving the correct
    # amount for the replacement input. If an attacker could decrease the amount of an
    # external input in the original transaction, then they could steal the fee from
    # the transaction without the user noticing.

    inp1 = messages.TxInputType(
        address_n=parse_path("49h/1h/0h/0/8"),
        amount=4973340,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        prev_hash=TXHASH_6673b7,
        prev_index=0,
        orig_hash=TXHASH_ed89ac,
        orig_index=0,
    )

    inp2 = messages.TxInputType(
        # Actually 49h/1h/0h/0/9, but we will make it look like it's external,
        # so that we can try out this scenario, i.e. not a part of the attack.
        amount=839318869,
        script_type=messages.InputScriptType.EXTERNAL,
        prev_hash=TXHASH_927784,
        prev_index=0,
        orig_hash=TXHASH_ed89ac,
        orig_index=1,
        script_pubkey=bytes.fromhex("a914eb227e547838e56792d92ef597244d8b33767c8f87"),
        script_sig=bytes.fromhex("160014681ea49259abb892460bf3373e8a0b43d877fa18"),
        witness=bytes.fromhex(
            "02483045022100d9c2d4364e104bf0d27886b4d7cd05f9a256bda8acbe84b7b2753f5c054b1a8602206a512575a89da5b5123e2769a5f73675b27b9f43d1a7b54bddeae039f6b83efa0121028cbc37e1816a23086fa738c8415def477e813e20f484dbbd6f5a33a37c322251"
        ),
    )

    # Attacker adds 30000, but it could even go to a new output.
    out1 = messages.TxOutputType(
        address="moE1dVYvebvtaMuNdXQKvu4UxUftLmS1Gt",
        amount=100000000 + 30000,
        orig_hash=TXHASH_ed89ac,
        orig_index=1,
    )

    # Change-output. Original fee was 90720, attacker steals 30000.
    out2 = messages.TxOutputType(
        address_n=parse_path("49h/1h/0h/1/6"),
        amount=4973340 + 839318869 - (100000000 + 30000) - 60720,
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
    )

    # Decrease the original amount of inp2 by 30000.
    # Also make the original inp2 look external (not a part of the attack).
    prev_tx_attack = TX_CACHE_TESTNET[TXHASH_ed89ac]
    prev_tx_attack.inputs[1].amount -= 30000
    prev_tx_attack.inputs[1].address_n = None
    prev_tx_attack.inputs[1].script_type = messages.InputScriptType.EXTERNAL
    prev_tx_attack.inputs[1].script_pubkey = bytes.fromhex(
        "a914eb227e547838e56792d92ef597244d8b33767c8f87"
    )

    prev_txes = {
        TXHASH_ed89ac: prev_tx_attack,
        TXHASH_6673b7: TX_CACHE_TESTNET[TXHASH_6673b7],
        TXHASH_927784: TX_CACHE_TESTNET[TXHASH_927784],
    }

    with pytest.raises(
        TrezorFailure, match="Original input does not match current input"
    ):
        btc.sign_tx(
            client,
            "Testnet",
            [inp1, inp2],
            [out1, out2],
            prev_txes=prev_txes,
        )


def test_p2wpkh_invalid_signature(client):
    # Ensure that transaction replacement fails when the original signature is invalid.

    # Original input with disabled RBF opt-in, i.e. we finalize the transaction.
    inp1 = messages.TxInputType(
        address_n=parse_path("84h/1h/0h/0/2"),
        amount=20000000,
        script_type=messages.InputScriptType.SPENDWITNESS,
        prev_hash=TXHASH_43d273,
        prev_index=1,
        orig_hash=TXHASH_70f987,
        orig_index=0,
        sequence=4294967294,
    )

    # Original external output (actually 84h/1h/0h/0/0).
    out1 = messages.TxOutputType(
        address="tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9",
        amount=100000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
        orig_hash=TXHASH_70f987,
        orig_index=0,
    )

    # Change output. We bump the fee from 141 to 200.
    out2 = messages.TxOutputType(
        address_n=parse_path("84h/1h/0h/1/1"),
        amount=20000000 - 100000 - 200,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
        orig_hash=TXHASH_70f987,
        orig_index=1,
    )

    # Invalidate the signature in the original witness.
    prev_tx_invalid = TX_CACHE_TESTNET[TXHASH_70f987]
    prev_tx_invalid.inputs[0].witness = bytearray(prev_tx_invalid.inputs[0].witness)
    prev_tx_invalid.inputs[0].witness[10] ^= 1
    prev_txes = {
        TXHASH_70f987: prev_tx_invalid,
        TXHASH_43d273: TX_CACHE_TESTNET[TXHASH_43d273],
    }

    with pytest.raises(TrezorFailure, match="Invalid signature"):
        btc.sign_tx(
            client,
            "Testnet",
            [inp1],
            [out1, out2],
            lock_time=1348713,
            prev_txes=prev_txes,
        )
