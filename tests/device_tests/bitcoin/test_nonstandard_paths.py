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
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from .signtx import forge_prevtx

VECTORS = (  # path, script_types
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
        "m/3h/100h/4/255",
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
VECTORS_MULTISIG = (  # paths, address_index
    # GreenAddress A m/[1,4]/address_index
    (("m/1", "m/1", "m/4"), [255]),
    # GreenAddress B m/3'/[1-100]'/[1,4]/address_index
    (("m/3h/100h/1", "m/3h/99h/1", "m/3h/98h/1"), [255]),
    # GreenAdress Sign A m/1195487518
    (("m/1195487518", "m/1195487518", "m/1195487518"), []),
    # GreenAdress Sign B m/1195487518/6/address_index
    (("m/1195487518/6", "m/1195487518/6", "m/1195487518/6"), [255]),
    # Unchained hardened m/45'/coin_type'/account'/[0-1000000]/change/address_index
    (
        ("m/45h/0h/63h/1000000", "m/45h/0h/62h/1000000", "m/45h/0h/61h/1000000"),
        [0, 255],
    ),
    # Unchained unhardened m/45'/coin_type/account/[0-1000000]/change/address_index
    (("m/45h/0/63/1000000", "m/45h/0/62/1000000", "m/45h/0/61/1000000"), [0, 255]),
    # Unchained deprecated m/45'/coin_type'/account'/[0-1000000]/address_index
    (("m/45h/0h/63h/1000000", "m/45h/0h/62h/1000000", "m/45h/0/61/1000000"), [255]),
    # Casa Paths
    (("m/45h/0/60/1", "m/45h/1/60/0", "m/45h/2/60/0"), [255]),
)


# Has AlwaysMatchingSchema but let's make sure the nonstandard paths are
# accepted in case we make this more restrictive in the future.
@pytest.mark.parametrize("path, script_types", VECTORS)
def test_getpublicnode(
    client: Client, path: str, script_types: list[messages.InputScriptType]
):
    for script_type in script_types:
        res = btc.get_public_node(
            client, parse_path(path), coin_name="Bitcoin", script_type=script_type
        )

        assert res.xpub


@pytest.mark.parametrize("chunkify", (True, False))
@pytest.mark.parametrize("path, script_types", VECTORS)
def test_getaddress(
    client: Client,
    chunkify: bool,
    path: str,
    script_types: list[messages.InputScriptType],
):
    for script_type in script_types:
        res = btc.get_address(
            client,
            "Bitcoin",
            parse_path(path),
            show_display=True,
            script_type=script_type,
            chunkify=chunkify,
        )

        assert res


@pytest.mark.parametrize("path, script_types", VECTORS)
def test_signmessage(
    client: Client, path: str, script_types: list[messages.InputScriptType]
):
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
def test_signtx(
    client: Client, path: str, script_types: list[messages.InputScriptType]
):
    address_n = parse_path(path)

    for script_type in script_types:
        address = btc.get_address(client, "Bitcoin", address_n, script_type=script_type)
        prevhash, prevtx = forge_prevtx([(address, 390_000)])
        inp1 = messages.TxInputType(
            address_n=address_n,
            amount=390_000,
            prev_hash=prevhash,
            prev_index=0,
            script_type=script_type,
        )

        out1 = messages.TxOutputType(
            address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
            amount=390_000 - 10_000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )

        _, serialized_tx = btc.sign_tx(
            client, "Bitcoin", [inp1], [out1], prev_txes={prevhash: prevtx}
        )

        assert serialized_tx.hex()


@pytest.mark.multisig
@pytest.mark.parametrize("paths, address_index", VECTORS_MULTISIG)
def test_getaddress_multisig(
    client: Client, paths: list[str], address_index: list[int]
):
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


@pytest.mark.multisig
@pytest.mark.parametrize("paths, address_index", VECTORS_MULTISIG)
def test_signtx_multisig(client: Client, paths: list[str], address_index: list[int]):
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

    address_n = parse_path(paths[0]) + address_index
    address = btc.get_address(
        client,
        "Bitcoin",
        address_n,
        multisig=multisig,
        script_type=messages.InputScriptType.SPENDMULTISIG,
    )

    prevhash, prevtx = forge_prevtx([(address, 20_000)])

    inp1 = messages.TxInputType(
        address_n=address_n,
        amount=20_000,
        prev_hash=prevhash,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDMULTISIG,
        multisig=multisig,
    )

    out1 = messages.TxOutputType(
        address="17kTB7qSk3MupQxWdiv5ZU3zcrZc2Azes1",
        amount=10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    sig, _ = btc.sign_tx(
        client, "Bitcoin", [inp1], [out1], prev_txes={prevhash: prevtx}
    )

    assert sig[0]
