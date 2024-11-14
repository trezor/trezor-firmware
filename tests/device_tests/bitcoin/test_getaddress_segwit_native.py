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
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

VECTORS = (  # coin, path, script_type, address
    (
        "Testnet",
        "m/84h/1h/0h/0/0",
        messages.InputScriptType.SPENDWITNESS,
        "tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9",
    ),
    (
        "Testnet",
        "m/84h/1h/0h/1/0",
        messages.InputScriptType.SPENDWITNESS,
        "tb1qejqxwzfld7zr6mf7ygqy5s5se5xq7vmt96jk9x",
    ),
    (
        "Bitcoin",
        "m/84h/0h/0h/0/0",
        messages.InputScriptType.SPENDWITNESS,
        "bc1qannfxke2tfd4l7vhepehpvt05y83v3qsf6nfkk",
    ),
    (
        "Bitcoin",
        "m/84h/0h/0h/1/0",
        messages.InputScriptType.SPENDWITNESS,
        "bc1qktmhrsmsenepnnfst8x6j27l0uqv7ggrg8x38q",
    ),
    (
        "Testnet",
        "m/86h/1h/0h/0/0",
        messages.InputScriptType.SPENDTAPROOT,
        "tb1pswrqtykue8r89t9u4rprjs0gt4qzkdfuursfnvqaa3f2yql07zmq8s8a5u",
    ),
    (
        "Testnet",
        "m/86h/1h/0h/1/0",
        messages.InputScriptType.SPENDTAPROOT,
        "tb1pn2d0yjeedavnkd8z8lhm566p0f2utm3lgvxrsdehnl94y34txmts5s7t4c",
    ),
    (
        "Bitcoin",
        "m/86h/0h/0h/0/0",
        messages.InputScriptType.SPENDTAPROOT,
        "bc1ptxs597p3fnpd8gwut5p467ulsydae3rp9z75hd99w8k3ljr9g9rqx6ynaw",
    ),
    (
        "Bitcoin",
        "m/86h/0h/0h/1/0",
        messages.InputScriptType.SPENDTAPROOT,
        "bc1pgypgja2hmcx2l6s2ssq75k6ev68ved6nujcspt47dgvkp8euc70s6uegk6",
    ),
    pytest.param(
        "Groestlcoin Testnet",
        "m/84h/1h/0h/0/0",
        messages.InputScriptType.SPENDWITNESS,
        "tgrs1qkvwu9g3k2pdxewfqr7syz89r3gj557l3ued7ja",
        marks=pytest.mark.altcoin,
    ),
    pytest.param(
        "Groestlcoin Testnet",
        "m/84h/1h/0h/1/0",
        messages.InputScriptType.SPENDWITNESS,
        "tgrs1qejqxwzfld7zr6mf7ygqy5s5se5xq7vmt9lkd57",
        marks=pytest.mark.altcoin,
    ),
    pytest.param(
        "Groestlcoin",
        "m/84h/17h/0h/0/0",
        messages.InputScriptType.SPENDWITNESS,
        "grs1qw4teyraux2s77nhjdwh9ar8rl9dt7zww8r6lne",
        marks=pytest.mark.altcoin,
    ),
    pytest.param(
        "Groestlcoin",
        "m/84h/17h/0h/1/0",
        messages.InputScriptType.SPENDWITNESS,
        "grs1qzfpwn55tvkxcw0xwfa0g8k2gtlzlgkcq3z000e",
        marks=pytest.mark.altcoin,
    ),
    pytest.param(
        "Groestlcoin Testnet",
        "m/86h/1h/0h/0/0",
        messages.InputScriptType.SPENDTAPROOT,
        "tgrs1pswrqtykue8r89t9u4rprjs0gt4qzkdfuursfnvqaa3f2yql07zmq5v2q7z",
        marks=pytest.mark.altcoin,
    ),
    pytest.param(
        "Groestlcoin",
        "m/86h/17h/0h/0/0",
        messages.InputScriptType.SPENDTAPROOT,
        "grs1pnacleslusvh6gdjd3j2y5kv3drq09038sww2zx4za68jssndmu6qkm698g",
        marks=pytest.mark.altcoin,
    ),
    pytest.param(
        "Elements",
        "m/84h/1h/0h/0/0",
        messages.InputScriptType.SPENDWITNESS,
        "ert1qkvwu9g3k2pdxewfqr7syz89r3gj557l3xp9k2v",
        marks=pytest.mark.altcoin,
    ),
)


BIP86_VECTORS = (  # path, address for "abandon ... abandon about" seed
    (
        "m/86h/0h/0h/0/0",
        "bc1p5cyxnuxmeuwuvkwfem96lqzszd02n6xdcjrs20cac6yqjjwudpxqkedrcr",
    ),
    (
        "m/86h/0h/0h/0/1",
        "bc1p4qhjn9zdvkux4e44uhx8tc55attvtyu358kutcqkudyccelu0was9fqzwh",
    ),
    (
        "m/86h/0h/0h/1/0",
        "bc1p3qkhfews2uk44qtvauqyr2ttdsw7svhkl9nkm9s9c3x4ax5h60wqwruhk7",
    ),
)


@pytest.mark.parametrize("show_display", (True, False))
@pytest.mark.parametrize("coin, path, script_type, address", VECTORS)
def test_show_segwit(
    client: Client,
    show_display: bool,
    coin: str,
    path: str,
    script_type: messages.InputScriptType,
    address: str,
):
    assert (
        btc.get_address(
            client,
            coin,
            parse_path(path),
            show_display,
            None,
            script_type=script_type,
        )
        == address
    )


# Tests https://github.com/bitcoin/bips/blob/master/bip-0086.mediawiki#test-vectors
@pytest.mark.setup_client(
    mnemonic="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
)
@pytest.mark.parametrize("path, address", BIP86_VECTORS)
def test_bip86(client: Client, path: str, address: str):
    assert (
        btc.get_address(
            client,
            "Bitcoin",
            parse_path(path),
            False,
            None,
            script_type=messages.InputScriptType.SPENDTAPROOT,
        )
        == address
    )


@pytest.mark.multisig
def test_show_multisig_3(client: Client):
    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/84h/1h/{index}h"), coin_name="Testnet"
        ).node
        for index in range(1, 4)
    ]
    multisig1 = messages.MultisigRedeemScriptType(
        nodes=nodes, address_n=[0, 0], signatures=[b"", b"", b""], m=2
    )
    multisig2 = messages.MultisigRedeemScriptType(
        nodes=nodes, address_n=[0, 1], signatures=[b"", b"", b""], m=2
    )
    for i in [1, 2, 3]:
        assert (
            btc.get_address(
                client,
                "Testnet",
                parse_path(f"m/84h/1h/{i}h/0/1"),
                False,
                multisig2,
                script_type=messages.InputScriptType.SPENDWITNESS,
            )
            == "tb1qauuv4e2pwjkr4ws5f8p20hu562jlqpe5h74whxqrwf7pufsgzcms9y8set"
        )
        assert (
            btc.get_address(
                client,
                "Testnet",
                parse_path(f"m/84h/1h/{i}h/0/0"),
                False,
                multisig1,
                script_type=messages.InputScriptType.SPENDWITNESS,
            )
            == "tb1qgvn67p4twmpqhs8c39tukmu9geamtf7x0z3flwf9rrw4ff3h6d2qt0czq3"
        )


@pytest.mark.multisig
@pytest.mark.parametrize("show_display", (True, False))
def test_multisig_missing(client: Client, show_display: bool):
    # Use account numbers 1, 2 and 3 to create a valid multisig,
    # but not containing the keys from account 0 used below.
    nodes = [
        btc.get_public_node(client, parse_path(f"m/84h/0h/{i}h")).node
        for i in range(1, 4)
    ]

    # Multisig with global suffix specification.
    multisig1 = messages.MultisigRedeemScriptType(
        nodes=nodes, address_n=[0, 0], signatures=[b"", b"", b""], m=2
    )

    # Multisig with per-node suffix specification.
    multisig2 = messages.MultisigRedeemScriptType(
        pubkeys=[
            messages.HDNodePathType(node=node, address_n=[0, 0]) for node in nodes
        ],
        signatures=[b"", b"", b""],
        m=2,
    )

    for multisig in (multisig1, multisig2):
        with pytest.raises(TrezorFailure):
            btc.get_address(
                client,
                "Bitcoin",
                parse_path("m/84h/0h/0h/0/0"),
                show_display=show_display,
                multisig=multisig,
                script_type=messages.InputScriptType.SPENDWITNESS,
            )
