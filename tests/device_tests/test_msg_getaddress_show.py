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
        client, tools.parse_path("45h/0/0"), coin_name="Bitcoin"
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
                tools.parse_path(f"45h/0/0/{i}"),
                show_display=True,
                multisig=multisig,
                script_type=messages.InputScriptType.SPENDMULTISIG,
            )
            == "35Q3tgZZfr9GhVpaqz7fbDK8WXV1V1KxfD"
        )


VECTORS_MULTISIG = (  # script_type, purpose48_type, address, xpubs, ignore_xpub_magic
    (
        messages.InputScriptType.SPENDMULTISIG,
        0,
        "33TU5DyVi2kFSGQUfmZxNHgPDPqruwdesY",
        [
            "xpub6EgGHjcvovyMw8xyoJw9ZRUfjGLS1KUmbjVqMKSNfM6E8hq4EbQ3CpBxfGCPsdxzXtCFuKCxYarzY1TYCG1cmPwq9ep548cM9Ws9rB8V8E8",
            "xpub6EexEtC6c2rN5QCpzrL2nUNGDfxizCi3kM1C2Mk5a6PfQs4H3F72C642M3XbnzycvvtD4U6vzn1nYPpH8VUmiREc2YuXP3EFgN1uLTrVEj4",
            "xpub6F6Tq7sVLDrhuV3SpvsVKrKofF6Hx7oKxWLFkN6dbepuMhuYueKUnQo7E972GJyeRHqPKu44V1C9zBL6KW47GXjuprhbNrPQahWAFKoL2rN",
        ],
        False,
    ),
    (
        messages.InputScriptType.SPENDMULTISIG,
        0,
        "33TU5DyVi2kFSGQUfmZxNHgPDPqruwdesY",
        [
            "xpub6EgGHjcvovyMw8xyoJw9ZRUfjGLS1KUmbjVqMKSNfM6E8hq4EbQ3CpBxfGCPsdxzXtCFuKCxYarzY1TYCG1cmPwq9ep548cM9Ws9rB8V8E8",
            "xpub6EexEtC6c2rN5QCpzrL2nUNGDfxizCi3kM1C2Mk5a6PfQs4H3F72C642M3XbnzycvvtD4U6vzn1nYPpH8VUmiREc2YuXP3EFgN1uLTrVEj4",
            "xpub6F6Tq7sVLDrhuV3SpvsVKrKofF6Hx7oKxWLFkN6dbepuMhuYueKUnQo7E972GJyeRHqPKu44V1C9zBL6KW47GXjuprhbNrPQahWAFKoL2rN",
        ],
        True,
    ),
    (
        messages.InputScriptType.SPENDP2SHWITNESS,
        1,
        "3PwoNRb1v7HxofcH6xfiq52nFrDarsn1ap",
        [
            "Ypub6kQcie2HXa5DFqmgCmad1Lg18pn3UwtXXyTKJkW3bGbQJuTYn55s7x4SVCSTRkjDzawFYP2rL9VkS2YChaN47d2XFyWsbEPevN9n9NXc3T3",
            "Ypub6kPJfnbTKfxDNwYqbNAijySLYe7ixrVZHn9QksvtwrqCbUoemq5x74A4bH33FWe8p8udC5F2B78JV4EfHYaMupWZhoQRXJ32Z2y7fhowkPA",
            "Ypub6kppG2Gr3rxZChPFhkMdPdLChewkPwLybPirJGBcJW1mRXeWdWvXLRP7xUcjJgTiGEQcJPKu8PTQMTtLXeiEjP7N2KGpamQnGUvBikJZvvP",
        ],
        False,
    ),
    (
        messages.InputScriptType.SPENDP2SHWITNESS,
        1,
        "3PwoNRb1v7HxofcH6xfiq52nFrDarsn1ap",
        [
            "xpub6EgGHjcvovyMyyRBRkL1yBEhF4bLKyDSJbHRc6LcqVP7dd5Qm1Y2QmYNfHXPsQrQMUkTvKSAzGkhRaJsgeo6AuEFZAi3bv7AkupGAt826Mt",
            "xpub6EexEtC6c2rN75CLpLv7hp12esw1ospU4PyX4DmUC5cuvCRWkmY7PsdzmN7yhAmKB2iqa1eLqEPFUc1LGd1Py6iHzzbbXykYPadbh8xQonD",
            "xpub6F6Tq7sVLDrhvq2kvj72MTttotm3ExftN1Yxbc2BYioUkFGNcTNgdEs48ZhfkLatd8DpgKjDnWiMM1f1Wj9GnfK6KWTzbT8J72afkGf7Y9T",
        ],
        True,
    ),
    (
        messages.InputScriptType.SPENDWITNESS,
        2,
        "bc1qqn9s63wly66rhzyz36hwzsa83augj5lve3ucqk5cpt5yvvze5ctsdfcg88",
        [
            "Zpub75Et2JhCgFchAwrkdQ2PWeCiEnLmQ8R8a8aANPL5r9a6L4VC9amvLtbmnZaEnS7m3YHd1ZnSYjKp1rFTZLm2cQ2CAuiEyNYaYWyeWEFGEmP",
            "Zpub75DZyTGNUMVhGRgG7GsoF2FrsAAM48dPMMfYSo9G7iRxUg9FyuG3nMUSeYMXSF2rHtDNpv8skZZyDNzBq5x5znFtsPSDoaAXk5zBUBfdhSh",
            "Zpub75f5ZgwmCYW37REirFNaE8DBg9qKJznqD498DsTAbX89Lk6tA98huCGM29mHAhwYTo1PSbWLQHXvsmMhDB8W9dFt3Eb2o6hT7HLDrcPebM5",
        ],
        False,
    ),
    (
        messages.InputScriptType.SPENDWITNESS,
        2,
        "bc1qqn9s63wly66rhzyz36hwzsa83augj5lve3ucqk5cpt5yvvze5ctsdfcg88",
        [
            "xpub6EgGHjcvovyN3nK921zAGPfuB41cJXkYRdt3tLGmiMyvbgHpss4X1eRZwShbEBb1znz2e2bCkCED87QZpin3sSYKbmCzQ9Sc7LaV98ngdeX",
            "xpub6EexEtC6c2rN9G8eVtqZzmj3oRqBxXxoCryRxk5wyvqnkHwtiBYeT7JEoRUsszW7F8unTNwdx2UNKe9J6Ty7Fpn2JEvyEM4ZJub274iiT1V",
            "xpub6F6Tq7sVLDrhzFh7EsLLysgNcRWADQ8F4ZT1jpPrTjXycMuWtRRJZx69B2tdcTQoR3ho54K6bkSKz2WoUZ9XQfn1U65nDsbUg6w4VZ5HWdA",
        ],
        True,
    ),
)


@pytest.mark.skip_t1
@pytest.mark.multisig
@pytest.mark.parametrize(
    "script_type, purpose48_type, address, xpubs, ignore_xpub_magic", VECTORS_MULTISIG
)
def test_show_multisig_xpubs(
    client, script_type, purpose48_type, address, xpubs, ignore_xpub_magic
):
    nodes = [
        btc.get_public_node(
            client,
            tools.parse_path(f"48h/0h/{i}h/{purpose48_type}h"),
            coin_name="Bitcoin",
        )
        for i in range(3)
    ]
    multisig = messages.MultisigRedeemScriptType(
        nodes=[n.node for n in nodes],
        signatures=[b"", b"", b""],
        address_n=[0, 0],
        m=2,
    )

    for i in range(3):

        def input_flow():
            yield  # show address
            lines = client.debug.wait_layout().lines
            assert lines[0] == "Multisig 2 of 3"
            assert "".join(lines[1:]) == address

            client.debug.press_no()
            yield  # show QR code
            assert client.debug.wait_layout().text.startswith("Qr")

            client.debug.press_no()
            yield  # show XPUB#1
            lines1 = client.debug.wait_layout().lines
            assert lines1[0] == "XPUB #1 " + ("(yours)" if i == 0 else "(cosigner)")
            client.debug.swipe_up()
            lines2 = client.debug.wait_layout().lines
            assert lines2[0] == "XPUB #1 " + ("(yours)" if i == 0 else "(cosigner)")
            assert "".join(lines1[1:] + lines2[1:]) == xpubs[0]

            client.debug.press_no()
            yield  # show XPUB#2
            lines1 = client.debug.wait_layout().lines
            assert lines1[0] == "XPUB #2 " + ("(yours)" if i == 1 else "(cosigner)")
            client.debug.swipe_up()
            lines2 = client.debug.wait_layout().lines
            assert lines2[0] == "XPUB #2 " + ("(yours)" if i == 1 else "(cosigner)")
            assert "".join(lines1[1:] + lines2[1:]) == xpubs[1]

            client.debug.press_no()
            yield  # show XPUB#3
            lines1 = client.debug.wait_layout().lines
            assert lines1[0] == "XPUB #3 " + ("(yours)" if i == 2 else "(cosigner)")
            client.debug.swipe_up()
            lines2 = client.debug.wait_layout().lines
            assert lines2[0] == "XPUB #3 " + ("(yours)" if i == 2 else "(cosigner)")
            assert "".join(lines1[1:] + lines2[1:]) == xpubs[2]

            client.debug.press_yes()

        with client:
            client.watch_layout()
            client.set_input_flow(input_flow)
            btc.get_address(
                client,
                "Bitcoin",
                tools.parse_path(f"48h/0h/{i}h/{purpose48_type}h/0/0"),
                show_display=True,
                multisig=multisig,
                script_type=script_type,
                ignore_xpub_magic=ignore_xpub_magic,
            )


@pytest.mark.multisig
def test_show_multisig_15(client):
    node = btc.get_public_node(
        client, tools.parse_path("45h/0/0"), coin_name="Bitcoin"
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
                tools.parse_path(f"45h/0/0/{i}"),
                show_display=True,
                multisig=multisig,
                script_type=messages.InputScriptType.SPENDMULTISIG,
            )
            == "3GG78bp1hA3mu9xv1vZLXiENmeabmi7WKQ"
        )
