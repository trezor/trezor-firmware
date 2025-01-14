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

from trezorlib import btc, device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import MultisigPubkeysOrder, SafetyCheckLevel
from trezorlib.tools import parse_path

from ... import bip32
from ...common import is_core
from ...input_flows import InputFlowConfirmAllWarnings


def getmultisig(chain, nr, xpubs):
    return messages.MultisigRedeemScriptType(
        nodes=[bip32.deserialize(xpub) for xpub in xpubs],
        address_n=[chain, nr],
        signatures=[b"", b"", b""],
        m=2,
    )


def test_btc(client: Client):
    assert (
        btc.get_address(client, "Bitcoin", parse_path("m/44h/0h/0h/0/0"))
        == "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL"
    )
    assert (
        btc.get_address(client, "Bitcoin", parse_path("m/44h/0h/0h/0/1"))
        == "1GWFxtwWmNVqotUPXLcKVL2mUKpshuJYo"
    )
    assert (
        btc.get_address(client, "Bitcoin", parse_path("m/44h/0h/0h/1/0"))
        == "1DyHzbQUoQEsLxJn6M7fMD8Xdt1XvNiwNE"
    )


@pytest.mark.altcoin
def test_ltc(client: Client):
    assert (
        btc.get_address(client, "Litecoin", parse_path("m/44h/2h/0h/0/0"))
        == "LcubERmHD31PWup1fbozpKuiqjHZ4anxcL"
    )
    assert (
        btc.get_address(client, "Litecoin", parse_path("m/44h/2h/0h/0/1"))
        == "LVWBmHBkCGNjSPHucvL2PmnuRAJnucmRE6"
    )
    assert (
        btc.get_address(client, "Litecoin", parse_path("m/44h/2h/0h/1/0"))
        == "LWj6ApswZxay4cJEJES2sGe7fLMLRvvv8h"
    )


def test_tbtc(client: Client):
    assert (
        btc.get_address(client, "Testnet", parse_path("m/44h/1h/0h/0/0"))
        == "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q"
    )
    assert (
        btc.get_address(client, "Testnet", parse_path("m/44h/1h/0h/0/1"))
        == "mopZWqZZyQc3F2Sy33cvDtJchSAMsnLi7b"
    )
    assert (
        btc.get_address(client, "Testnet", parse_path("m/44h/1h/0h/1/0"))
        == "mm6kLYbGEL1tGe4ZA8xacfgRPdW1NLjCbZ"
    )


@pytest.mark.altcoin
def test_bch(client: Client):
    assert (
        btc.get_address(client, "Bcash", parse_path("m/44h/145h/0h/0/0"))
        == "bitcoincash:qr08q88p9etk89wgv05nwlrkm4l0urz4cyl36hh9sv"
    )
    assert (
        btc.get_address(client, "Bcash", parse_path("m/44h/145h/0h/0/1"))
        == "bitcoincash:qr23ajjfd9wd73l87j642puf8cad20lfmqdgwvpat4"
    )
    assert (
        btc.get_address(client, "Bcash", parse_path("m/44h/145h/0h/1/0"))
        == "bitcoincash:qzc5q87w069lzg7g3gzx0c8dz83mn7l02scej5aluw"
    )


@pytest.mark.altcoin
def test_grs(client: Client):
    assert (
        btc.get_address(client, "Groestlcoin", parse_path("m/44h/17h/0h/0/0"))
        == "Fj62rBJi8LvbmWu2jzkaUX1NFXLEqDLoZM"
    )
    assert (
        btc.get_address(client, "Groestlcoin", parse_path("m/44h/17h/0h/1/0"))
        == "FmRaqvVBRrAp2Umfqx9V1ectZy8gw54QDN"
    )
    assert (
        btc.get_address(client, "Groestlcoin", parse_path("m/44h/17h/0h/1/1"))
        == "Fmhtxeh7YdCBkyQF7AQG4QnY8y3rJg89di"
    )


@pytest.mark.altcoin
def test_tgrs(client: Client):
    assert (
        btc.get_address(client, "Groestlcoin Testnet", parse_path("m/44h/1h/0h/0/0"))
        == "mvbu1Gdy8SUjTenqerxUaZyYjmvedc787y"
    )
    assert (
        btc.get_address(client, "Groestlcoin Testnet", parse_path("m/44h/1h/0h/1/0"))
        == "mm6kLYbGEL1tGe4ZA8xacfgRPdW1LMq8cN"
    )
    assert (
        btc.get_address(client, "Groestlcoin Testnet", parse_path("m/44h/1h/0h/1/1"))
        == "mjXZwmEi1z1MzveZrKUAo4DBgbdq6ZhGD6"
    )


@pytest.mark.altcoin
def test_elements(client: Client):
    assert (
        btc.get_address(client, "Elements", parse_path("m/44h/1h/0h/0/0"))
        == "2dpWh6jbhAowNsQ5agtFzi7j6nKscj6UnEr"
    )


@pytest.mark.models("core")
def test_address_mac(client: Client):
    resp = btc.get_authenticated_address(
        client, "Bitcoin", parse_path("m/44h/0h/0h/1/0")
    )
    assert resp.address == "1DyHzbQUoQEsLxJn6M7fMD8Xdt1XvNiwNE"
    assert (
        resp.mac.hex()
        == "9cf7c230041d6ed95b8273bd32e023d3f227ec8c44257f6463c743a4b4add028"
    )

    resp = btc.get_authenticated_address(
        client, "Testnet", parse_path("m/44h/1h/0h/1/0")
    )
    assert resp.address == "mm6kLYbGEL1tGe4ZA8xacfgRPdW1NLjCbZ"
    assert (
        resp.mac.hex()
        == "4375089e50423505dc3480e6e85b0ba37a52bd1e009db5d260b6329f22c950d9"
    )

    # Script type mismatch.
    resp = btc.get_authenticated_address(
        client, "Bitcoin", parse_path("m/84h/0h/0h/0/0"), show_display=False
    )
    assert resp.mac is None


@pytest.mark.models("core")
@pytest.mark.altcoin
def test_altcoin_address_mac(client: Client):
    resp = btc.get_authenticated_address(
        client, "Litecoin", parse_path("m/44h/2h/0h/1/0")
    )
    assert resp.address == "LWj6ApswZxay4cJEJES2sGe7fLMLRvvv8h"
    assert (
        resp.mac.hex()
        == "eaf47182d7ae17d2046ec2e204bc5b67477db20a5eaea3cec5393c25664bc4d2"
    )

    resp = btc.get_authenticated_address(
        client, "Bcash", parse_path("m/44h/145h/0h/1/0")
    )
    assert resp.address == "bitcoincash:qzc5q87w069lzg7g3gzx0c8dz83mn7l02scej5aluw"
    assert (
        resp.mac.hex()
        == "46d8e369b499a9dc62eb9e4472f4a12640ae0fb7a63c1a4dde6752123b2b7274"
    )

    resp = btc.get_authenticated_address(
        client, "Groestlcoin", parse_path("m/44h/17h/0h/1/1")
    )
    assert resp.address == "Fmhtxeh7YdCBkyQF7AQG4QnY8y3rJg89di"
    assert (
        resp.mac.hex()
        == "08d67c5f1ee20fd03f3e5aa26f798574716c122238ac280e33a6f3787d531552"
    )


@pytest.mark.multisig
def test_multisig_pubkeys_order(client: Client):
    xpub_internal = btc.get_public_node(client, parse_path("m/45h/0")).xpub
    xpub_external = btc.get_public_node(client, parse_path("m/45h/1")).xpub

    multisig_unsorted_1 = messages.MultisigRedeemScriptType(
        nodes=[bip32.deserialize(xpub) for xpub in [xpub_external, xpub_internal]],
        address_n=[0, 0],
        signatures=[b"", b""],
        m=2,
        pubkeys_order=MultisigPubkeysOrder.PRESERVED,
    )

    multisig_unsorted_2 = messages.MultisigRedeemScriptType(
        nodes=[bip32.deserialize(xpub) for xpub in [xpub_internal, xpub_external]],
        address_n=[0, 0],
        signatures=[b"", b""],
        m=2,
        pubkeys_order=MultisigPubkeysOrder.PRESERVED,
    )

    multisig_sorted_1 = messages.MultisigRedeemScriptType(
        nodes=[bip32.deserialize(xpub) for xpub in [xpub_external, xpub_internal]],
        address_n=[0, 0],
        signatures=[b"", b""],
        m=2,
        pubkeys_order=MultisigPubkeysOrder.LEXICOGRAPHIC,
    )

    multisig_sorted_2 = messages.MultisigRedeemScriptType(
        nodes=[bip32.deserialize(xpub) for xpub in [xpub_internal, xpub_external]],
        address_n=[0, 0],
        signatures=[b"", b""],
        m=2,
        pubkeys_order=MultisigPubkeysOrder.LEXICOGRAPHIC,
    )

    address_unsorted_1 = "3DpiomhFpTzGJZNksqn67pW5AUV1xHBMG1"
    address_unsorted_2 = "3DKeup4KhFpvJPpqnPRdZMte73YZC3v8dS"

    assert (
        btc.get_address(
            client, "Bitcoin", parse_path("m/45h/0/0/0"), multisig=multisig_unsorted_1
        )
        == address_unsorted_1
    )
    assert (
        btc.get_address(
            client, "Bitcoin", parse_path("m/45h/0/0/0"), multisig=multisig_unsorted_2
        )
        == address_unsorted_2
    )
    assert (
        btc.get_address(
            client, "Bitcoin", parse_path("m/45h/0/0/0"), multisig=multisig_sorted_1
        )
        == address_unsorted_2
    )
    assert (
        btc.get_address(
            client, "Bitcoin", parse_path("m/45h/0/0/0"), multisig=multisig_sorted_2
        )
        == address_unsorted_2
    )


@pytest.mark.multisig
def test_multisig(client: Client):
    xpubs = []
    for n in range(1, 4):
        node = btc.get_public_node(client, parse_path(f"m/44h/0h/{n}h"))
        xpubs.append(node.xpub)

    for nr in range(1, 4):
        with client:
            if is_core(client):
                IF = InputFlowConfirmAllWarnings(client)
                client.set_input_flow(IF.get())
            assert (
                btc.get_address(
                    client,
                    "Bitcoin",
                    parse_path(f"m/44h/0h/{nr}h/0/0"),
                    show_display=(nr == 1),
                    multisig=getmultisig(0, 0, xpubs=xpubs),
                )
                == "3Pdz86KtfJBuHLcSv4DysJo4aQfanTqCzG"
            )
            assert (
                btc.get_address(
                    client,
                    "Bitcoin",
                    parse_path(f"m/44h/0h/{nr}h/1/0"),
                    show_display=(nr == 1),
                    multisig=getmultisig(1, 0, xpubs=xpubs),
                )
                == "36gP3KVx1ooStZ9quZDXbAF3GCr42b2zzd"
            )


@pytest.mark.multisig
@pytest.mark.parametrize("show_display", (True, False))
def test_multisig_missing(client: Client, show_display):
    # Use account numbers 1, 2 and 3 to create a valid multisig,
    # but not containing the keys from account 0 used below.
    nodes = [
        btc.get_public_node(client, parse_path(f"m/44h/0h/{i}h")).node
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
        with client, pytest.raises(TrezorFailure):
            if is_core(client):
                IF = InputFlowConfirmAllWarnings(client)
                client.set_input_flow(IF.get())
            btc.get_address(
                client,
                "Bitcoin",
                parse_path("m/44h/0h/0h/0/0"),
                show_display=show_display,
                multisig=multisig,
            )


@pytest.mark.altcoin
@pytest.mark.multisig
def test_bch_multisig(client: Client):
    xpubs = []
    for n in range(1, 4):
        node = btc.get_public_node(
            client, parse_path(f"m/44h/145h/{n}h"), coin_name="Bcash"
        )
        xpubs.append(node.xpub)

    for nr in range(1, 4):
        with client:
            if is_core(client):
                IF = InputFlowConfirmAllWarnings(client)
                client.set_input_flow(IF.get())
            assert (
                btc.get_address(
                    client,
                    "Bcash",
                    parse_path(f"m/44h/145h/{nr}h/0/0"),
                    show_display=(nr == 1),
                    multisig=getmultisig(0, 0, xpubs=xpubs),
                )
                == "bitcoincash:pqguz4nqq64jhr5v3kvpq4dsjrkda75hwy86gq0qzw"
            )
            assert (
                btc.get_address(
                    client,
                    "Bcash",
                    parse_path(f"m/44h/145h/{nr}h/1/0"),
                    show_display=(nr == 1),
                    multisig=getmultisig(1, 0, xpubs=xpubs),
                )
                == "bitcoincash:pp6kcpkhua7789g2vyj0qfkcux3yvje7euhyhltn0a"
            )


def test_public_ckd(client: Client):
    node = btc.get_public_node(client, parse_path("m/44h/0h/0h")).node
    node_sub1 = btc.get_public_node(client, parse_path("m/44h/0h/0h/1/0")).node
    node_sub2 = bip32.public_ckd(node, [1, 0])

    assert node_sub1.chain_code == node_sub2.chain_code
    assert node_sub1.public_key == node_sub2.public_key

    address1 = btc.get_address(client, "Bitcoin", parse_path("m/44h/0h/0h/1/0"))
    address2 = bip32.get_address(node_sub2, 0)

    assert address2 == "1DyHzbQUoQEsLxJn6M7fMD8Xdt1XvNiwNE"
    assert address1 == address2


def test_invalid_path(client: Client):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        # slip44 id mismatch
        btc.get_address(
            client, "Bitcoin", parse_path("m/44h/111h/0h/0/0"), show_display=True
        )


def test_unknown_path(client: Client):
    UNKNOWN_PATH = parse_path("m/44h/9h/0h/0/0")
    with client:
        client.set_expected_responses([messages.Failure])

        with pytest.raises(TrezorFailure, match="Forbidden key path"):
            # account number is too high
            btc.get_address(client, "Bitcoin", UNKNOWN_PATH, show_display=True)

    # disable safety checks
    device.apply_settings(client, safety_checks=SafetyCheckLevel.PromptTemporarily)

    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(
                    code=messages.ButtonRequestType.UnknownDerivationPath
                ),
                messages.ButtonRequest(code=messages.ButtonRequestType.Address),
                messages.Address,
            ]
        )
        if is_core(client):
            IF = InputFlowConfirmAllWarnings(client)
            client.set_input_flow(IF.get())
        # try again with a warning
        btc.get_address(client, "Bitcoin", UNKNOWN_PATH, show_display=True)

    with client:
        # no warning is displayed when the call is silent
        client.set_expected_responses([messages.Address])
        btc.get_address(client, "Bitcoin", UNKNOWN_PATH, show_display=False)


@pytest.mark.altcoin
def test_crw(client: Client):
    assert (
        btc.get_address(client, "Crown", parse_path("m/44h/72h/0h/0/0"))
        == "CRWYdvZM1yXMKQxeN3hRsAbwa7drfvTwys48"
    )


@pytest.mark.multisig
def test_multisig_different_paths(client: Client):
    nodes = [
        btc.get_public_node(client, parse_path(f"m/45h/{i}"), coin_name="Bitcoin").node
        for i in range(2)
    ]

    multisig = messages.MultisigRedeemScriptType(
        pubkeys=[
            messages.HDNodePathType(node=node, address_n=[0, i])
            for i, node in enumerate(nodes)
        ],
        signatures=[b"", b"", b""],
        m=2,
    )

    with pytest.raises(
        Exception, match="Using different paths for different xpubs is not allowed"
    ):
        with client:
            if is_core(client):
                IF = InputFlowConfirmAllWarnings(client)
                client.set_input_flow(IF.get())
            btc.get_address(
                client,
                "Bitcoin",
                parse_path("m/45h/0/0/0"),
                show_display=True,
                multisig=multisig,
                script_type=messages.InputScriptType.SPENDMULTISIG,
            )

    device.apply_settings(client, safety_checks=SafetyCheckLevel.PromptTemporarily)
    with client:
        if is_core(client):
            IF = InputFlowConfirmAllWarnings(client)
            client.set_input_flow(IF.get())
        btc.get_address(
            client,
            "Bitcoin",
            parse_path("m/45h/0/0/0"),
            show_display=True,
            multisig=multisig,
            script_type=messages.InputScriptType.SPENDMULTISIG,
        )
