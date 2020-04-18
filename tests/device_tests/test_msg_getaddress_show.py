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

from trezorlib import btc, ckd_public as bip32, messages, tools

from ..common import MNEMONIC12


class TestMsgGetaddressShow:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_show(self, client):
        assert (
            btc.get_address(client, "Bitcoin", [1], show_display=True)
            == "1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb"
        )
        assert (
            btc.get_address(client, "Bitcoin", [2], show_display=True)
            == "15AeAhtNJNKyowK8qPHwgpXkhsokzLtUpG"
        )
        assert (
            btc.get_address(client, "Bitcoin", [3], show_display=True)
            == "1CmzyJp9w3NafXMSEFH4SLYUPAVCSUrrJ5"
        )

    @pytest.mark.multisig
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_show_multisig_3(self, client):
        node = bip32.deserialize(
            "xpub661MyMwAqRbcF1zGijBb2K6x9YiJPh58xpcCeLvTxMX6spkY3PcpJ4ABcCyWfskq5DDxM3e6Ez5ePCqG5bnPUXR4wL8TZWyoDaUdiWW7bKy"
        )
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
                    client, "Bitcoin", [i], show_display=True, multisig=multisig
                )
                == "3E7GDtuHqnqPmDgwH59pVC7AvySiSkbibz"
            )

    @pytest.mark.skip_t1
    @pytest.mark.multisig
    def test_show_multisig_xpubs(self, client):
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

                client.debug.press_no()
                yield  # show XPUB#2
                lines = client.debug.wait_layout().lines
                assert lines[0] == "XPUB #2 " + ("(yours)" if i == 1 else "(others)")
                assert lines[1:] == xpubs[1]
                # just for UI test
                client.debug.swipe_up()

                client.debug.press_no()
                yield  # show XPUB#3
                lines = client.debug.wait_layout().lines
                assert lines[0] == "XPUB #3 " + ("(yours)" if i == 2 else "(others)")
                assert lines[1:] == xpubs[2]
                # just for UI test
                client.debug.swipe_up()

                client.debug.press_yes()

            with client:
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
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_show_multisig_15(self, client):
        node = bip32.deserialize(
            "xpub661MyMwAqRbcF1zGijBb2K6x9YiJPh58xpcCeLvTxMX6spkY3PcpJ4ABcCyWfskq5DDxM3e6Ez5ePCqG5bnPUXR4wL8TZWyoDaUdiWW7bKy"
        )

        pubs = []
        for x in range(15):
            pubs.append(messages.HDNodePathType(node=node, address_n=[x]))

        multisig = messages.MultisigRedeemScriptType(
            pubkeys=pubs, signatures=[b""] * 15, m=15
        )

        for i in range(15):
            assert (
                btc.get_address(
                    client, "Bitcoin", [i], show_display=True, multisig=multisig
                )
                == "3QaKF8zobqcqY8aS6nxCD5ZYdiRfL3RCmU"
            )
