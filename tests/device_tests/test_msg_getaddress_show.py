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

from trezorlib import btc, messages, tools

VECTORS = (  # path, script_type, address
    (
        "m/44h/0h/12h/0/0",
        messages.InputScriptType.SPENDADDRESS,
        "1FM6Kz3oT3GoGv65jNpU8AFFun8nHAXrPk",
    ),
    (
        "m/49h/0h/12h/0/0",
        messages.InputScriptType.SPENDP2SHWITNESS,
        "3HfEUkuwmtZ87XzowkiD5nMp5Q3hqKXZ2i",
    ),
    (
        "m/84h/0h/12h/0/0",
        messages.InputScriptType.SPENDWITNESS,
        "bc1qduvap743hcl7twn8u6f9l0u8y7x83965xy0raj",
    ),
)


@pytest.mark.parametrize("path, script_type, address", VECTORS)
def test_show(client, path, script_type, address):
    assert (
        btc.get_address(
            client,
            "Bitcoin",
            tools.parse_path(path),
            script_type=script_type,
            show_display=True,
        )
        == address
    )


@pytest.mark.multisig
def test_show_multisig_3(client):
    node = btc.get_public_node(
        client, tools.parse_path("44h/0h/0h/0"), coin_name="Bitcoin"
    ).node
    multisig = messages.MultisigRedeemScriptType(
        pubkeys=[
            messages.HDNodePathType(node=node, address_n=[1]),
            messages.HDNodePathType(node=node, address_n=[2]),
            messages.HDNodePathType(node=node, address_n=[3]),
        ],
        signatures=[b"", b"", b""],
        m=2,
    )

    for i in [1, 2, 3]:
        assert (
            btc.get_address(
                client,
                "Bitcoin",
                tools.parse_path(f"44h/0h/0h/0/{i}"),
                show_display=True,
                multisig=multisig,
            )
            == "36AvLYugbb9CsN8sQ5k7kJ2diWF54msYKs"
        )


@pytest.mark.skip_t1
@pytest.mark.multisig
def test_show_multisig_xpubs(client):
    nodes = [
        btc.get_public_node(
            client, tools.parse_path(f"48h/0h/{i}h"), coin_name="Bitcoin"
        )
        for i in range(3)
    ]
    multisig = messages.MultisigRedeemScriptType(
        nodes=[n.node for n in nodes],
        signatures=[b"", b"", b""],
        address_n=[0, 0],
        m=2,
    )

    xpubs = [[n.xpub[i * 16 : (i + 1) * 16] for i in range(5)] for n in nodes]

    for i in range(3):

        def input_flow():
            yield  # show address
            assert client.debug.wait_layout().lines == [
                "Multisig 2 of 3",
                "34yJV2b2GtbmxfZNw",
                "jPyuyUYkUbUnogqa8",
            ]

            client.debug.press_no()
            yield  # show QR code
            assert client.debug.wait_layout().text.startswith("Qr")

            client.debug.press_no()
            yield  # show XPUB#1
            lines = client.debug.wait_layout().lines
            assert lines[0] == "XPUB #1 " + ("(yours)" if i == 0 else "(others)")
            assert lines[1:] == xpubs[0]
            # just for UI test
            client.debug.swipe_up()
            client.debug.wait_layout()

            client.debug.press_no()
            yield  # show XPUB#2
            lines = client.debug.wait_layout().lines
            assert lines[0] == "XPUB #2 " + ("(yours)" if i == 1 else "(others)")
            assert lines[1:] == xpubs[1]
            # just for UI test
            client.debug.swipe_up()
            client.debug.wait_layout()

            client.debug.press_no()
            yield  # show XPUB#3
            lines = client.debug.wait_layout().lines
            assert lines[0] == "XPUB #3 " + ("(yours)" if i == 2 else "(others)")
            assert lines[1:] == xpubs[2]
            # just for UI test
            client.debug.swipe_up()
            client.debug.wait_layout()

            client.debug.press_yes()

        with client:
            client.watch_layout()
            client.set_input_flow(input_flow)
            btc.get_address(
                client,
                "Bitcoin",
                tools.parse_path(f"48h/0h/{i}h/0/0"),
                show_display=True,
                multisig=multisig,
                script_type=messages.InputScriptType.SPENDMULTISIG,
            )


@pytest.mark.multisig
def test_show_multisig_15(client):
    node = btc.get_public_node(
        client, tools.parse_path("44h/0h/0h/0"), coin_name="Bitcoin"
    ).node

    pubs = [messages.HDNodePathType(node=node, address_n=[x]) for x in range(15)]

    multisig = messages.MultisigRedeemScriptType(
        pubkeys=pubs, signatures=[b""] * 15, m=15
    )

    for i in range(15):
        assert (
            btc.get_address(
                client,
                "Bitcoin",
                tools.parse_path(f"44h/0h/0h/0/{i}"),
                show_display=True,
                multisig=multisig,
            )
            == "3D9EDNTZde5KizWdjidELFzx7xtrcdM7AG"
        )
