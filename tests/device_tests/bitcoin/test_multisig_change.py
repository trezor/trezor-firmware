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
from trezorlib.tools import H_, parse_path

from ... import bip32
from ...common import MNEMONIC12
from ...tx_cache import TxCache
from ..signtx import request_finished, request_input, request_meta, request_output

B = messages.ButtonRequestType
TX_API = TxCache("Testnet")
# NOTE: This test case was migrated from Testnet to Bitcoin, because we
# disabled testnet for BIP-45 paths. So we are still using the Testnet TxCache
# here, but everything else has been changed to Bitcoin mainnet.

TXHASH_16c6c8 = bytes.fromhex(
    "16c6c8471b8db7a628f2b2bb86bfeefae1766463ce8692438c7fd3fce3f43ce5"
)
TXHASH_d80c34 = bytes.fromhex(
    "d80c34ee14143a8bf61125102b7ef594118a3796cad670fa8ee15080ae155318"
)
TXHASH_b0946d = bytes.fromhex(
    "b0946dc27ba308a749b11afecc2018980af18f79e89ad6b080b58220d856f739"
)

pytestmark = [pytest.mark.multisig, pytest.mark.setup_client(mnemonic=MNEMONIC12)]


NODE_EXT1 = bip32.deserialize(
    "xpub69qexv5TppjJQtXwSGeGXNtgGWyUzvsHACMt4Rr61Be4CmCf55eFcuXX828aySNuNR7hQYUCvUgZpioNxfs2HTAZWUUSFywhErg7JfTPv3Y"
)
# m/1 => 02c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e
# m/2 => 0375b9dfaad928ce1a7eed88df7c084e67d99e9ab74332419458a9a45779706801

NODE_EXT2 = bip32.deserialize(
    "xpub69qexv5TppjJRiLLK2K1FZNCFcErkXprCo3jabCXMiqX5CFF4LHedwcXvXkTuBL9tFLWVxuGWrdeerXjiWpC1gynTNUaySDsr8SU5xMpj5R"
)
# m/1 => 0388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1
# m/2 => 03a04f945d5a3685729dde697d574076de4bdf38e904f813b22a851548e1110fc0

NODE_EXT3 = bip32.deserialize(
    "xpub69qexv5TppjJVYtxFKSBFxcVGyaC8VJDa1RugAYwEDLVUBuaXrVgznvQB44piM8MRerfVf1pNCBK1L1NzhyKd4Ay25BVZX3S8twWfZDxmz7"
)
# m/1 => 02e0c21e2a7cf00b94c5421725acff97f9826598b91f2340c5ddda730caca7d648
# m/2 => 03928301ffb8c0d7a364b794914c716ba3107cc78a6fe581028b0d8638b22e8573

NODE_INT = bip32.deserialize(
    "xpub69qexv5TppjJNEK5bfX8vQ6ASXDUQ5PohSajrHgeknHZ4SJipn7edmpRmiiBLLDtPur71mekZFazhgas8rkUMnS7quk5qp64TLLV8ShrxZJ"
)
# m/1 => 03f91460d79e4e463d7d90cb75254bcd62b515a99a950574c721efdc5f711dff35
# m/2 => 038caebd6f753bbbd2bb1f3346a43cd32140648583673a31d62f2dfb56ad0ab9e3

# ext1 + ext2 + int
#   redeemscript (2 of 3): 522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c1210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653ae
#   multisig address: 2N9W4z9AhAPaHghtqVQPbaTAGHdbrhKeBQw
#   tx: 16c6c8471b8db7a628f2b2bb86bfeefae1766463ce8692438c7fd3fce3f43ce5
#   input 0: 0.5 BTC

# ext1 + int + ext2
#   redeemscript (2 of 3): 522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a6210388460dc439f4c8f5bcfc268c36e11b4375cad5c3535c336cfdf8c32c3afad5c153ae
#   multisig address: 2NDBG6QXQLtnQ3jRGkrqo53BiCeXfQXLdj4
#   tx: d80c34ee14143a8bf61125102b7ef594118a3796cad670fa8ee15080ae155318
#   input 0: 0.345 BTC

# ext1 + ext3 + int
#   redeemscript (2 of 3): 522102c0d0c5fee952620757c6128dbf327c996cd72ed3358d15d6518a1186099bc15e2102e0c21e2a7cf00b94c5421725acff97f9826598b91f2340c5ddda730caca7d648210338d78612e990f2eea0c426b5e48a8db70b9d7ed66282b3b26511e0b1c75515a653ae
#   multisig address: 2MvwPWfp2XPU3S1cMwgEMKBPUw38VP5SBE4
#   tx: b0946dc27ba308a749b11afecc2018980af18f79e89ad6b080b58220d856f739
#   input 1: 0.555 BTC

multisig_in1 = messages.MultisigRedeemScriptType(
    nodes=[NODE_EXT2, NODE_EXT1, NODE_INT],
    address_n=[0, 0],
    signatures=[b"", b"", b""],
    m=2,
)

multisig_in2 = messages.MultisigRedeemScriptType(
    nodes=[NODE_EXT1, NODE_EXT2, NODE_INT],
    address_n=[0, 1],
    signatures=[b"", b"", b""],
    m=2,
)

multisig_in3 = messages.MultisigRedeemScriptType(
    nodes=[NODE_EXT1, NODE_EXT3, NODE_INT],
    address_n=[0, 1],
    signatures=[b"", b"", b""],
    m=2,
)

# 2N9W4z9AhAPaHghtqVQPbaTAGHdbrhKeBQw
INP1 = messages.TxInputType(
    address_n=[H_(45), 0, 0, 0],
    amount=50000000,
    prev_hash=TXHASH_16c6c8,
    prev_index=1,
    script_type=messages.InputScriptType.SPENDMULTISIG,
    multisig=multisig_in1,
)

# 2NDBG6QXQLtnQ3jRGkrqo53BiCeXfQXLdj4
INP2 = messages.TxInputType(
    address_n=[H_(45), 0, 0, 1],
    amount=34500000,
    prev_hash=TXHASH_d80c34,
    prev_index=0,
    script_type=messages.InputScriptType.SPENDMULTISIG,
    multisig=multisig_in2,
)

# 2MvwPWfp2XPU3S1cMwgEMKBPUw38VP5SBE4
INP3 = messages.TxInputType(
    address_n=[H_(45), 0, 0, 1],
    amount=55500000,
    prev_hash=TXHASH_b0946d,
    prev_index=0,
    script_type=messages.InputScriptType.SPENDMULTISIG,
    multisig=multisig_in3,
)


def _responses(INP1, INP2, change=0):
    resp = [
        request_input(0),
        request_input(1),
        request_output(0),
    ]
    if change != 1:
        resp.append(messages.ButtonRequest(code=B.ConfirmOutput))
    resp.append(request_output(1))
    if change != 2:
        resp.append(messages.ButtonRequest(code=B.ConfirmOutput))
    resp += [
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_meta(INP1.prev_hash),
        request_input(0, INP1.prev_hash),
        request_output(0, INP1.prev_hash),
        request_output(1, INP1.prev_hash),
        request_input(1),
        request_meta(INP2.prev_hash),
        request_input(0, INP2.prev_hash),
        request_output(0, INP2.prev_hash),
        request_output(1, INP2.prev_hash),
        request_input(0),
        request_input(1),
        request_output(0),
        request_output(1),
        request_input(0),
        request_input(1),
        request_output(0),
        request_output(1),
        request_output(0),
        request_output(1),
        request_finished(),
    ]
    return resp


# both outputs are external
def test_external_external(client):
    out1 = messages.TxOutputType(
        address="1F8yBZB2NZhPZvJekhjTwjhQRRvQeTjjXr",
        amount=40000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address="1H7uXJQTVwXca2BXF2opTrvuZapk8Cm8zY",
        amount=44000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(_responses(INP1, INP2))
        _, serialized_tx = btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )

    assert (
        serialized_tx.hex()
        == "0100000002e53cf4e3fcd37f8c439286ce636476e1faeebf86bbb2f228a6b78d1b47c8c61601000000b400473044022064f13801744a6c21b694f62cdb5d834e852f13ecf85ed4d0a56ba279571c24e3022010fab4cb05bdd7b24c8376dda4f62a418548eea6eb483e58675fa06e0d5c642c014c69522103dc07026aacb5918dac4e09f9da8290d0ae22161699636c22cace78082116a7792103e70db185fad69c2971f0107a42930e5d82a9ed3a11b922a96fdfc4124b63e54c2103f3fe007a1e34ac76c1a2528e9149f90f9f93739929797afab6a8e18d682fa71053aeffffffff185315ae8050e18efa70d6ca96378a1194f57e2b102511f68b3a1414ee340cd800000000b4004730440220727b2522268f913acd213c507d7801b146e5b6cef666ad44b769c26d6c762e4d022021c0c2e9e8298dee2a490d956f7ab1b2d3160c1e37a50cc6d19a5e62eb484fc9014c6952210297ad8a5df42f9e362ef37d9a4ddced89d8f7a143690649aa0d0ff049c7daca842103ed1fd93989595d7ad4b488efd05a22c0239482c9a20923f2f214a38e54f6c41a2103f91460d79e4e463d7d90cb75254bcd62b515a99a950574c721efdc5f711dff3553aeffffffff02005a6202000000001976a9149b139230e4fe91c05a37ec334dc8378f3dbe377088ac00639f02000000001976a914b0d05a10926a7925508febdbab9a5bd4cda8c8f688ac00000000"
    )


# first external, second internal
def test_external_internal(client):
    out1 = messages.TxOutputType(
        address="1F8yBZB2NZhPZvJekhjTwjhQRRvQeTjjXr",
        amount=40000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=parse_path("45'/0/1/1"),
        amount=44000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(_responses(INP1, INP2, change=2))
        _, serialized_tx = btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )

    assert (
        serialized_tx.hex()
        == "0100000002e53cf4e3fcd37f8c439286ce636476e1faeebf86bbb2f228a6b78d1b47c8c61601000000b400473044022064f13801744a6c21b694f62cdb5d834e852f13ecf85ed4d0a56ba279571c24e3022010fab4cb05bdd7b24c8376dda4f62a418548eea6eb483e58675fa06e0d5c642c014c69522103dc07026aacb5918dac4e09f9da8290d0ae22161699636c22cace78082116a7792103e70db185fad69c2971f0107a42930e5d82a9ed3a11b922a96fdfc4124b63e54c2103f3fe007a1e34ac76c1a2528e9149f90f9f93739929797afab6a8e18d682fa71053aeffffffff185315ae8050e18efa70d6ca96378a1194f57e2b102511f68b3a1414ee340cd800000000b4004730440220727b2522268f913acd213c507d7801b146e5b6cef666ad44b769c26d6c762e4d022021c0c2e9e8298dee2a490d956f7ab1b2d3160c1e37a50cc6d19a5e62eb484fc9014c6952210297ad8a5df42f9e362ef37d9a4ddced89d8f7a143690649aa0d0ff049c7daca842103ed1fd93989595d7ad4b488efd05a22c0239482c9a20923f2f214a38e54f6c41a2103f91460d79e4e463d7d90cb75254bcd62b515a99a950574c721efdc5f711dff3553aeffffffff02005a6202000000001976a9149b139230e4fe91c05a37ec334dc8378f3dbe377088ac00639f02000000001976a914b0d05a10926a7925508febdbab9a5bd4cda8c8f688ac00000000"
    )


# first internal, second external
def test_internal_external(client):
    out1 = messages.TxOutputType(
        address_n=parse_path("45'/0/1/0"),
        amount=40000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address="1H7uXJQTVwXca2BXF2opTrvuZapk8Cm8zY",
        amount=44000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(_responses(INP1, INP2, change=1))
        _, serialized_tx = btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )

    assert (
        serialized_tx.hex()
        == "0100000002e53cf4e3fcd37f8c439286ce636476e1faeebf86bbb2f228a6b78d1b47c8c61601000000b400473044022064f13801744a6c21b694f62cdb5d834e852f13ecf85ed4d0a56ba279571c24e3022010fab4cb05bdd7b24c8376dda4f62a418548eea6eb483e58675fa06e0d5c642c014c69522103dc07026aacb5918dac4e09f9da8290d0ae22161699636c22cace78082116a7792103e70db185fad69c2971f0107a42930e5d82a9ed3a11b922a96fdfc4124b63e54c2103f3fe007a1e34ac76c1a2528e9149f90f9f93739929797afab6a8e18d682fa71053aeffffffff185315ae8050e18efa70d6ca96378a1194f57e2b102511f68b3a1414ee340cd800000000b4004730440220727b2522268f913acd213c507d7801b146e5b6cef666ad44b769c26d6c762e4d022021c0c2e9e8298dee2a490d956f7ab1b2d3160c1e37a50cc6d19a5e62eb484fc9014c6952210297ad8a5df42f9e362ef37d9a4ddced89d8f7a143690649aa0d0ff049c7daca842103ed1fd93989595d7ad4b488efd05a22c0239482c9a20923f2f214a38e54f6c41a2103f91460d79e4e463d7d90cb75254bcd62b515a99a950574c721efdc5f711dff3553aeffffffff02005a6202000000001976a9149b139230e4fe91c05a37ec334dc8378f3dbe377088ac00639f02000000001976a914b0d05a10926a7925508febdbab9a5bd4cda8c8f688ac00000000"
    )


# both outputs are external
def test_multisig_external_external(client):
    out1 = messages.TxOutputType(
        address="3B23k4kFBRtu49zvpG3Z9xuFzfpHvxBcwt",
        amount=40000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address="3PkXLsY7AUZCrCKGvX8FfP2EawowUBMbcg",
        amount=44000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(_responses(INP1, INP2))
        _, serialized_tx = btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )

    assert (
        serialized_tx.hex()
        == "0100000002e53cf4e3fcd37f8c439286ce636476e1faeebf86bbb2f228a6b78d1b47c8c61601000000b400473044022059394e0dfcb2d2f4a6108703f801545ca5a820c0ac6a1859d0a3854813de55fa02207b6a57d70b82932ff58163336c461653a2dc82c78ed8157159e5178ac7325390014c69522103dc07026aacb5918dac4e09f9da8290d0ae22161699636c22cace78082116a7792103e70db185fad69c2971f0107a42930e5d82a9ed3a11b922a96fdfc4124b63e54c2103f3fe007a1e34ac76c1a2528e9149f90f9f93739929797afab6a8e18d682fa71053aeffffffff185315ae8050e18efa70d6ca96378a1194f57e2b102511f68b3a1414ee340cd800000000b40047304402205a911685f5b974b2fc4a19d5ce056218773a4d20b5eaae2c2f9594929308182002201e03449f5a8813ec19f408bf1b6f4f334886d6fcf9920e300fd7678ef0724f81014c6952210297ad8a5df42f9e362ef37d9a4ddced89d8f7a143690649aa0d0ff049c7daca842103ed1fd93989595d7ad4b488efd05a22c0239482c9a20923f2f214a38e54f6c41a2103f91460d79e4e463d7d90cb75254bcd62b515a99a950574c721efdc5f711dff3553aeffffffff02005a62020000000017a91466528dd543f94d162c8111d2ec248d25ba9b90948700639f020000000017a914f1fc92c0aed1712911c70a2e09ac15ff0922652f8700000000"
    )


# inputs match, change matches (first is change)
def test_multisig_change_match_first(client):
    multisig_out1 = messages.MultisigRedeemScriptType(
        nodes=[NODE_EXT2, NODE_EXT1, NODE_INT],
        address_n=[1, 0],
        signatures=[b"", b"", b""],
        m=2,
    )

    out1 = messages.TxOutputType(
        address_n=[H_(45), 0, 1, 0],
        multisig=multisig_out1,
        amount=40000000,
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
    )

    out2 = messages.TxOutputType(
        address="3PkXLsY7AUZCrCKGvX8FfP2EawowUBMbcg",
        amount=44000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(_responses(INP1, INP2, change=1))
        _, serialized_tx = btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )

    assert (
        serialized_tx.hex()
        == "0100000002e53cf4e3fcd37f8c439286ce636476e1faeebf86bbb2f228a6b78d1b47c8c61601000000b400473044022059394e0dfcb2d2f4a6108703f801545ca5a820c0ac6a1859d0a3854813de55fa02207b6a57d70b82932ff58163336c461653a2dc82c78ed8157159e5178ac7325390014c69522103dc07026aacb5918dac4e09f9da8290d0ae22161699636c22cace78082116a7792103e70db185fad69c2971f0107a42930e5d82a9ed3a11b922a96fdfc4124b63e54c2103f3fe007a1e34ac76c1a2528e9149f90f9f93739929797afab6a8e18d682fa71053aeffffffff185315ae8050e18efa70d6ca96378a1194f57e2b102511f68b3a1414ee340cd800000000b40047304402205a911685f5b974b2fc4a19d5ce056218773a4d20b5eaae2c2f9594929308182002201e03449f5a8813ec19f408bf1b6f4f334886d6fcf9920e300fd7678ef0724f81014c6952210297ad8a5df42f9e362ef37d9a4ddced89d8f7a143690649aa0d0ff049c7daca842103ed1fd93989595d7ad4b488efd05a22c0239482c9a20923f2f214a38e54f6c41a2103f91460d79e4e463d7d90cb75254bcd62b515a99a950574c721efdc5f711dff3553aeffffffff02005a62020000000017a91466528dd543f94d162c8111d2ec248d25ba9b90948700639f020000000017a914f1fc92c0aed1712911c70a2e09ac15ff0922652f8700000000"
    )


# inputs match, change matches (second is change)
def test_multisig_change_match_second(client):
    multisig_out2 = messages.MultisigRedeemScriptType(
        nodes=[NODE_EXT1, NODE_EXT2, NODE_INT],
        address_n=[1, 1],
        signatures=[b"", b"", b""],
        m=2,
    )

    out1 = messages.TxOutputType(
        address="3B23k4kFBRtu49zvpG3Z9xuFzfpHvxBcwt",
        amount=40000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=[H_(45), 0, 1, 1],
        multisig=multisig_out2,
        amount=44000000,
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
    )

    with client:
        client.set_expected_responses(_responses(INP1, INP2, change=2))
        _, serialized_tx = btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )

    assert (
        serialized_tx.hex()
        == "0100000002e53cf4e3fcd37f8c439286ce636476e1faeebf86bbb2f228a6b78d1b47c8c61601000000b400473044022059394e0dfcb2d2f4a6108703f801545ca5a820c0ac6a1859d0a3854813de55fa02207b6a57d70b82932ff58163336c461653a2dc82c78ed8157159e5178ac7325390014c69522103dc07026aacb5918dac4e09f9da8290d0ae22161699636c22cace78082116a7792103e70db185fad69c2971f0107a42930e5d82a9ed3a11b922a96fdfc4124b63e54c2103f3fe007a1e34ac76c1a2528e9149f90f9f93739929797afab6a8e18d682fa71053aeffffffff185315ae8050e18efa70d6ca96378a1194f57e2b102511f68b3a1414ee340cd800000000b40047304402205a911685f5b974b2fc4a19d5ce056218773a4d20b5eaae2c2f9594929308182002201e03449f5a8813ec19f408bf1b6f4f334886d6fcf9920e300fd7678ef0724f81014c6952210297ad8a5df42f9e362ef37d9a4ddced89d8f7a143690649aa0d0ff049c7daca842103ed1fd93989595d7ad4b488efd05a22c0239482c9a20923f2f214a38e54f6c41a2103f91460d79e4e463d7d90cb75254bcd62b515a99a950574c721efdc5f711dff3553aeffffffff02005a62020000000017a91466528dd543f94d162c8111d2ec248d25ba9b90948700639f020000000017a914f1fc92c0aed1712911c70a2e09ac15ff0922652f8700000000"
    )


# inputs match, change mismatches (second tries to be change but isn't)
def test_multisig_mismatch_change(client):
    multisig_out2 = messages.MultisigRedeemScriptType(
        nodes=[NODE_EXT1, NODE_INT, NODE_EXT3],
        address_n=[1, 0],
        signatures=[b"", b"", b""],
        m=2,
    )

    out1 = messages.TxOutputType(
        address="3B23k4kFBRtu49zvpG3Z9xuFzfpHvxBcwt",
        amount=40000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=[H_(45), 0, 1, 0],
        multisig=multisig_out2,
        amount=44000000,
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
    )

    with client:
        client.set_expected_responses(_responses(INP1, INP2))
        _, serialized_tx = btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP2],
            [out1, out2],
            prev_txes=TX_API,
        )

    assert (
        serialized_tx.hex()
        == "0100000002e53cf4e3fcd37f8c439286ce636476e1faeebf86bbb2f228a6b78d1b47c8c61601000000b40047304402207f9992cc0230527faf54ec6bd233307db82bc8fac039dcee418bc6feb4e96a3a02206bb4cb157ad27c123277328a877572563a45d70b844d9ab07cc42238112f8c2a014c69522103dc07026aacb5918dac4e09f9da8290d0ae22161699636c22cace78082116a7792103e70db185fad69c2971f0107a42930e5d82a9ed3a11b922a96fdfc4124b63e54c2103f3fe007a1e34ac76c1a2528e9149f90f9f93739929797afab6a8e18d682fa71053aeffffffff185315ae8050e18efa70d6ca96378a1194f57e2b102511f68b3a1414ee340cd800000000b400473044022078a41bfa87d72d6ba810d84bf568b5a29acf8b851ba6c3a8dbff079b34a7feb0022037b770c776db0b6c883c38a684a121b90a59ed1958774cbf64de70e53e29639f014c6952210297ad8a5df42f9e362ef37d9a4ddced89d8f7a143690649aa0d0ff049c7daca842103ed1fd93989595d7ad4b488efd05a22c0239482c9a20923f2f214a38e54f6c41a2103f91460d79e4e463d7d90cb75254bcd62b515a99a950574c721efdc5f711dff3553aeffffffff02005a62020000000017a91466528dd543f94d162c8111d2ec248d25ba9b90948700639f020000000017a914e6a3e2fbadb7f559f8d20c46aceae78c96fcf1d18700000000"
    )


# inputs mismatch, change matches with first input
def test_multisig_mismatch_inputs(client):
    multisig_out1 = messages.MultisigRedeemScriptType(
        nodes=[NODE_EXT2, NODE_EXT1, NODE_INT],
        address_n=[1, 0],
        signatures=[b"", b"", b""],
        m=2,
    )

    out1 = messages.TxOutputType(
        address_n=[H_(45), 0, 1, 0],
        multisig=multisig_out1,
        amount=40000000,
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
    )

    out2 = messages.TxOutputType(
        address="3PkXLsY7AUZCrCKGvX8FfP2EawowUBMbcg",
        amount=65000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(_responses(INP1, INP3))
        _, serialized_tx = btc.sign_tx(
            client,
            "Bitcoin",
            [INP1, INP3],
            [out1, out2],
            prev_txes=TX_API,
        )

    assert (
        serialized_tx.hex()
        == "0100000002e53cf4e3fcd37f8c439286ce636476e1faeebf86bbb2f228a6b78d1b47c8c61601000000b500483045022100d907b9339951c96ef4515ef7aff8b3c28c4c8c5875d7421aa1de9f3a94e3508302205cdc311a6c91dfbb74f1a9a940a994a65dbfb0cf6dedcaaaeee839e0b8fd016d014c69522103dc07026aacb5918dac4e09f9da8290d0ae22161699636c22cace78082116a7792103e70db185fad69c2971f0107a42930e5d82a9ed3a11b922a96fdfc4124b63e54c2103f3fe007a1e34ac76c1a2528e9149f90f9f93739929797afab6a8e18d682fa71053aeffffffff39f756d82082b580b0d69ae8798ff10a981820ccfe1ab149a708a37bc26d94b000000000b500483045022100fdad4a47d15f47cc364fe0cbed11b1ced1f9ef210bc1bd413ec4384f630c63720220752e4f09ea4e5e6623f5ebe89b3983ec6e5702f63f9bce696f10b2d594d23532014c6952210297ad8a5df42f9e362ef37d9a4ddced89d8f7a143690649aa0d0ff049c7daca842103b6321a1194e5cc47b6b7edc3f67a096e6f71ccb72440f84f390b6e98df0ea8ec2103f91460d79e4e463d7d90cb75254bcd62b515a99a950574c721efdc5f711dff3553aeffffffff02005a62020000000017a91466528dd543f94d162c8111d2ec248d25ba9b90948740d2df030000000017a914f1fc92c0aed1712911c70a2e09ac15ff0922652f8700000000"
    )
