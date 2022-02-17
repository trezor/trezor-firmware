# This file is part of the Trezor project.
#
# Copyright (C) 2022 SatoshiLabs and contributors
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

from trezorlib import bech32, btc, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import hash_160_to_bc_address, parse_path

from ...tx_cache import TxCache

TX_CACHE_MAINNET = TxCache("Bitcoin")

TXHASH_0dac36 = bytes.fromhex(
    "0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5"
)

VECTORS = [
    (
        messages.LightningNetworkSwapType(
            invoice="lnbc538340n1p3q7l23pp57vysk3kakcfynz09du0zy87zy7n4gc6czqettc7c5v9v2fsrs9nqdpa2pskjepqw3hjq3r0deshgefqw3hjqjzjgcs8vv3qyq5y7unyv4ezqj2y8gszjxqy9ghlcqpjsp50lm6njtrm9qlyaac8252x4s4l3eu0aryx7zjjw4zrq6hgpk2evwqrzjqtesdx359t3gswn09838tur09zjk5m4zutvk7kyg5vnxg3xu74ptvzhchqqq3kgqqyqqqqqqqqqqqqgq9q9qyyssqlg84727az93gg8n37gv994w3r6dj0u8dk55qjlstappyuehq3mqjcafkyj2a39xp0w34mnzy04hzqnct7fecd380wfa0kc0en8v006sqxqchh5",
            htlc=bytes.fromhex(
                "02528a57b9b55e86f08562b2e49fe52649924600f865e14a41defac5cdc8d4a3ea"
            ),
            cltv=725891,
            swap_script_type=messages.InputScriptType.SPENDP2SHWITNESS,
            # bc1qannfxke2tfd4l7vhepehpvt05y83v3qsf6nfkk
            refund_address_n=parse_path("m/84h/0h/0h/0/0"),
            refund_script_type=messages.InputScriptType.SPENDWITNESS,
        ),
        "3NtRY64WfQk2vZy8GUhwQzzMmyY9ZhNEVi",
        "0100000001b5f59e2273c85b93aa9deff9bba5d7deace78610d3b0fb892a7ba6d86f36ac0d000000006b483045022100b67aeab2efbd533606b6b808d7a990ca04ec73f84947d086ef954f36bb16425e02201578ce2f893f8c63812fc8438165044d68c4a2abca40f2f4e7ecd36f739bedf6012103d7f3a07085bee09697cf03125d5c8760dfed65403dba787f1d1d8b1251af2cbeffffffff0160ea00000000000017a914e882ed93fcb8ba83b088a04ff4180035671ef39d8700000000",
    ),
    (
        messages.LightningNetworkSwapType(
            invoice="lnbc538340n1p3q7l23pp57vysk3kakcfynz09du0zy87zy7n4gc6czqettc7c5v9v2fsrs9nqdpa2pskjepqw3hjq3r0deshgefqw3hjqjzjgcs8vv3qyq5y7unyv4ezqj2y8gszjxqy9ghlcqpjsp50lm6njtrm9qlyaac8252x4s4l3eu0aryx7zjjw4zrq6hgpk2evwqrzjqtesdx359t3gswn09838tur09zjk5m4zutvk7kyg5vnxg3xu74ptvzhchqqq3kgqqyqqqqqqqqqqqqgq9q9qyyssqlg84727az93gg8n37gv994w3r6dj0u8dk55qjlstappyuehq3mqjcafkyj2a39xp0w34mnzy04hzqnct7fecd380wfa0kc0en8v006sqxqchh5",
            htlc=bytes.fromhex(
                "02528a57b9b55e86f08562b2e49fe52649924600f865e14a41defac5cdc8d4a3ea"
            ),
            cltv=725891,
            swap_script_type=messages.InputScriptType.SPENDWITNESS,
            # bc1qannfxke2tfd4l7vhepehpvt05y83v3qsf6nfkk
            refund_address_n=parse_path("m/84h/0h/0h/0/0"),
            refund_script_type=messages.InputScriptType.SPENDWITNESS,
        ),
        "bc1qx40dk7j6nkk0m8ffy5u93uujvf2jtqqqd9905l8t7fjtwsggu0rs0vmpd2",
        "0100000001b5f59e2273c85b93aa9deff9bba5d7deace78610d3b0fb892a7ba6d86f36ac0d000000006a47304402200828f923298a73dde0a8e385e078964bd97063b89d0d216b767fff94fecc301202200805908bcf4147f53e7b4e5a54de294a24874a4331ae141705c6ea203cb7429f012103d7f3a07085bee09697cf03125d5c8760dfed65403dba787f1d1d8b1251af2cbeffffffff0160ea000000000000220020355edb7a5a9dacfd9d29253858f3926255258000694afa7cebf264b74108e3c700000000",
    ),
    (
        messages.LightningNetworkSwapType(
            invoice="lnbc538340n1p3q7l23pp57vysk3kakcfynz09du0zy87zy7n4gc6czqettc7c5v9v2fsrs9nqdpa2pskjepqw3hjq3r0deshgefqw3hjqjzjgcs8vv3qyq5y7unyv4ezqj2y8gszjxqy9ghlcqpjsp50lm6njtrm9qlyaac8252x4s4l3eu0aryx7zjjw4zrq6hgpk2evwqrzjqtesdx359t3gswn09838tur09zjk5m4zutvk7kyg5vnxg3xu74ptvzhchqqq3kgqqyqqqqqqqqqqqqgq9q9qyyssqlg84727az93gg8n37gv994w3r6dj0u8dk55qjlstappyuehq3mqjcafkyj2a39xp0w34mnzy04hzqnct7fecd380wfa0kc0en8v006sqxqchh5",
            htlc=bytes.fromhex(
                "03bf9df301a514a83c0ccfea0e62951b19897fbb98f1612d56588edf1edc1bdf2a"
            ),
            cltv=725893,
            swap_script_type=messages.InputScriptType.SPENDP2SHWITNESS,
            # 1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL
            refund_address_n=parse_path("m/44h/0h/0h/0/0"),
            refund_script_type=messages.InputScriptType.SPENDADDRESS,
        ),
        "31jjHe38fsZ4HHuBbCbqpbrhsD3TxCCY4D",
        "0100000001b5f59e2273c85b93aa9deff9bba5d7deace78610d3b0fb892a7ba6d86f36ac0d000000006a47304402206c601351f1a21306ec4328da857cb7edbbe8c7b32e2ded19ad2888be3e010f7802200277a031944415a2f4d43b9dfb3f2aa7ee0f68603df91fc5356db8caa2557933012103d7f3a07085bee09697cf03125d5c8760dfed65403dba787f1d1d8b1251af2cbeffffffff0160ea00000000000017a91400835c51593132ba72c4e25b14fac7b412e6f2838700000000",
    ),
    (
        messages.LightningNetworkSwapType(
            invoice="lnbc538340n1p3q7l23pp57vysk3kakcfynz09du0zy87zy7n4gc6czqettc7c5v9v2fsrs9nqdpa2pskjepqw3hjq3r0deshgefqw3hjqjzjgcs8vv3qyq5y7unyv4ezqj2y8gszjxqy9ghlcqpjsp50lm6njtrm9qlyaac8252x4s4l3eu0aryx7zjjw4zrq6hgpk2evwqrzjqtesdx359t3gswn09838tur09zjk5m4zutvk7kyg5vnxg3xu74ptvzhchqqq3kgqqyqqqqqqqqqqqqgq9q9qyyssqlg84727az93gg8n37gv994w3r6dj0u8dk55qjlstappyuehq3mqjcafkyj2a39xp0w34mnzy04hzqnct7fecd380wfa0kc0en8v006sqxqchh5",
            htlc=bytes.fromhex(
                "03bf9df301a514a83c0ccfea0e62951b19897fbb98f1612d56588edf1edc1bdf2a"
            ),
            cltv=725893,
            swap_script_type=messages.InputScriptType.SPENDWITNESS,
            # 1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL
            refund_address_n=parse_path("m/44h/0h/0h/0/0"),
            refund_script_type=messages.InputScriptType.SPENDADDRESS,
        ),
        "bc1qagpvv4x8h5g0dr3v0fuvv43hqshchm8pa0fuhujkyc4sxz85fu8ssc08kc",
        "0100000001b5f59e2273c85b93aa9deff9bba5d7deace78610d3b0fb892a7ba6d86f36ac0d000000006a47304402200bb063f6d0c56fffdca77555bc63598c9ddbcbf80e9b5ba112648cfd62b681bb0220446ffc34429a62f675432cc037b138eeb8c8c518760b2f4618eac41caafe4f8f012103d7f3a07085bee09697cf03125d5c8760dfed65403dba787f1d1d8b1251af2cbeffffffff0160ea000000000000220020ea02c654c7bd10f68e2c7a78c65637042f8bece1ebd3cbf256262b0308f44f0f00000000",
    ),
]


def test_lnswap(client: Client):
    # input tx: 0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5
    # address = 1H2CRJBrDMhkvCGZMW7T4oQwYbL8eVuh7p
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/5h/0/9"),
        amount=63_988,
        prev_hash=TXHASH_0dac36,
        prev_index=0,
    )

    for lnswap, swap_address, tx in VECTORS:

        out1 = messages.TxOutputType(
            script_type=messages.OutputScriptType.PAYTOLNSWAP,
            lnswap=lnswap,
            amount=60_000,
            address=swap_address,
        )

        with client:
            _, serialized_tx = btc.sign_tx(
                client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
            )
        assert serialized_tx.hex() == tx
        if lnswap.swap_script_type == messages.InputScriptType.SPENDWITNESS:
            output_script = bytes.fromhex(tx[-76:-8])
            output_address = bech32.encode("bc", output_script[0], output_script[2:])
        else:  # messages.InputScriptType.SPENDP2SHWITNESS
            output_script = tx[-54:-8]
            output_address = hash_160_to_bc_address(
                bytes.fromhex(output_script[4:-2]), 5
            )
        assert swap_address == output_address
