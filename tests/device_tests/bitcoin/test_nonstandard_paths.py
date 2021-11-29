# This file is part of the Trezor project.
#
# Copyright (C) 2012-2021 SatoshiLabs and contributors
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
from trezorlib.tools import parse_path

from ...tx_cache import TxCache

TX_CACHE_MAINNET = TxCache("Bitcoin")

TXHASH_6189e3 = bytes.fromhex(
    "6189e3febb5a21cee8b725aa1ef04ffce7e609448446d3a8d6f483c634ef5315"
)
TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)


VECTORS = (
    # GreenAddress A m/[1,4]/address_index
    (
        "m/4/255",
        (
            messages.InputScriptType.SPENDADDRESS,
            messages.InputScriptType.SPENDWITNESS,
            messages.InputScriptType.SPENDP2SHWITNESS,
        ),
    ),
    # GreenAddress B m/3'/[1-100]'/[1,4]/address_index
    (
        "m/3'/100'/4/255",
        (
            messages.InputScriptType.SPENDADDRESS,
            messages.InputScriptType.SPENDWITNESS,
            messages.InputScriptType.SPENDP2SHWITNESS,
        ),
    ),
    # GreenAdress Sign A m/1195487518
    (
        "m/1195487518",
        (
            messages.InputScriptType.SPENDADDRESS,
            messages.InputScriptType.SPENDWITNESS,
            messages.InputScriptType.SPENDP2SHWITNESS,
        ),
    ),
    # GreenAdress Sign B m/1195487518/6/address_index
    (
        "m/1195487518/6/255",
        (
            messages.InputScriptType.SPENDADDRESS,
            messages.InputScriptType.SPENDWITNESS,
            messages.InputScriptType.SPENDP2SHWITNESS,
        ),
    ),
    # Casa m/49/coin_type/account/change/address_index
    (
        "m/49/0/63/0/255",
        (messages.InputScriptType.SPENDP2SHWITNESS,),
    ),
)

# 2-of-3 multisig, first path is ours
VECTORS_MULTISIG = (
    # GreenAddress A m/[1,4]/address_index
    (("m/1", "m/1", "m/4"), [255]),
    # GreenAddress B m/3'/[1-100]'/[1,4]/address_index
    (("m/3'/100'/1", "m/3'/99'/1", "m/3'/98'/1"), [255]),
    # GreenAdress Sign A m/1195487518
    (("m/1195487518", "m/1195487518", "m/1195487518"), []),
    # GreenAdress Sign B m/1195487518/6/address_index
    (("m/1195487518/6", "m/1195487518/6", "m/1195487518/6"), [255]),
    # Unchained hardened m/45'/coin_type'/account'/[0-1000000]/change/address_index
    (
        ("m/45'/0'/63'/1000000", "m/45'/0'/62'/1000000", "m/45'/0'/61'/1000000"),
        [0, 255],
    ),
    # Unchained unhardened m/45'/coin_type/account/[0-1000000]/change/address_index
    (("m/45'/0/63/1000000", "m/45'/0/62/1000000", "m/45'/0/61/1000000"), [0, 255]),
    # Unchained deprecated m/45'/coin_type'/account'/[0-1000000]/address_index
    (("m/45'/0'/63'/1000000", "m/45'/0'/62'/1000000", "m/45'/0/61/1000000"), [255]),
)


# Has AlwaysMatchingSchema but let's make sure the nonstandard paths are
# accepted in case we make this more restrictive in the future.
@pytest.mark.parametrize("path, script_types", VECTORS)
def test_getpublicnode(client, path, script_types):
    for script_type in script_types:
        res = btc.get_public_node(
            client, parse_path(path), coin_name="Bitcoin", script_type=script_type
        )

        assert res.xpub


@pytest.mark.parametrize("path, script_types", VECTORS)
def test_getaddress(client, path, script_types):
    for script_type in script_types:
        res = btc.get_address(
            client,
            "Bitcoin",
            parse_path(path),
            show_display=True,
            script_type=script_type,
        )

        assert res


@pytest.mark.parametrize("path, script_types", VECTORS)
def test_signmessage(client, path, script_types):
    for script_type in script_types:
        sig = btc.sign_message(
            client,
            coin_name="Bitcoin",
            n=parse_path(path),
            script_type=script_type,
            message="This is an example of a signed message.",
        )

        assert sig.signature


@pytest.mark.parametrize("path, script_types", VECTORS)
def test_signtx(client, path, script_types):
    # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
    # input 0: 0.0039 BTC

    for script_type in script_types:
        inp1 = messages.TxInputType(
            address_n=parse_path(path),
            amount=390000,
            prev_hash=TXHASH_d5f65e,
            prev_index=0,
            script_type=script_type,
        )

        out1 = messages.TxOutputType(
            address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
            amount=390000 - 10000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        _, serialized_tx = btc.sign_tx(
            client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
        )

        assert serialized_tx.hex()


@pytest.mark.multisig
@pytest.mark.parametrize("paths, address_index", VECTORS_MULTISIG)
def test_getaddress_multisig(client, paths, address_index):
    pubs = [
        messages.HDNodePathType(
            node=btc.get_public_node(
                client, parse_path(path), coin_name="Bitcoin"
            ).node,
            address_n=address_index,
        )
        for path in paths
    ]
    multisig = messages.MultisigRedeemScriptType(pubkeys=pubs, m=2)

    address = btc.get_address(
        client,
        "Bitcoin",
        parse_path(paths[0]) + address_index,
        show_display=True,
        multisig=multisig,
        script_type=messages.InputScriptType.SPENDMULTISIG,
    )

    assert address


# NOTE: we're signing input using the wrong key (and possibly script type) so
#       the test is going to fail if we make firmware stricter about this
@pytest.mark.multisig
@pytest.mark.parametrize("paths, address_index", VECTORS_MULTISIG)
def test_signtx_multisig(client, paths, address_index):
    pubs = [
        messages.HDNodePathType(
            node=btc.get_public_node(
                client, parse_path(path), coin_name="Bitcoin"
            ).node,
            address_n=address_index,
        )
        for path in paths
    ]
    signatures = [b""] * 3
    multisig = messages.MultisigRedeemScriptType(
        pubkeys=pubs, signatures=signatures, m=2
    )

    out1 = messages.TxOutputType(
        address="17kTB7qSk3MupQxWdiv5ZU3zcrZc2Azes1",
        amount=10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    inp1 = messages.TxInputType(
        address_n=parse_path(paths[0]) + address_index,
        amount=20000,
        prev_hash=TXHASH_6189e3,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDMULTISIG,
        multisig=multisig,
    )

    sig, _ = btc.sign_tx(client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET)

    assert sig[0]
