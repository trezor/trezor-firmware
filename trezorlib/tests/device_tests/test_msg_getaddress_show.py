# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from trezorlib import btc, messages as proto

from ..support import ckd_public as bip32
from .common import TrezorTest


class TestMsgGetaddressShow(TrezorTest):
    def test_show(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert (
            btc.get_address(self.client, "Bitcoin", [1], show_display=True)
            == "1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb"
        )
        assert (
            btc.get_address(self.client, "Bitcoin", [2], show_display=True)
            == "15AeAhtNJNKyowK8qPHwgpXkhsokzLtUpG"
        )
        assert (
            btc.get_address(self.client, "Bitcoin", [3], show_display=True)
            == "1CmzyJp9w3NafXMSEFH4SLYUPAVCSUrrJ5"
        )

    def test_show_multisig_3(self):
        self.setup_mnemonic_nopin_nopassphrase()

        node = bip32.deserialize(
            "xpub661MyMwAqRbcF1zGijBb2K6x9YiJPh58xpcCeLvTxMX6spkY3PcpJ4ABcCyWfskq5DDxM3e6Ez5ePCqG5bnPUXR4wL8TZWyoDaUdiWW7bKy"
        )
        multisig = proto.MultisigRedeemScriptType(
            pubkeys=[
                proto.HDNodePathType(node=node, address_n=[1]),
                proto.HDNodePathType(node=node, address_n=[2]),
                proto.HDNodePathType(node=node, address_n=[3]),
            ],
            signatures=[b"", b"", b""],
            m=2,
        )

        for i in [1, 2, 3]:
            assert (
                btc.get_address(
                    self.client, "Bitcoin", [i], show_display=True, multisig=multisig
                )
                == "3E7GDtuHqnqPmDgwH59pVC7AvySiSkbibz"
            )

    def test_show_multisig_15(self):
        self.setup_mnemonic_nopin_nopassphrase()

        node = bip32.deserialize(
            "xpub661MyMwAqRbcF1zGijBb2K6x9YiJPh58xpcCeLvTxMX6spkY3PcpJ4ABcCyWfskq5DDxM3e6Ez5ePCqG5bnPUXR4wL8TZWyoDaUdiWW7bKy"
        )

        pubs = []
        for x in range(15):
            pubs.append(proto.HDNodePathType(node=node, address_n=[x]))

        multisig = proto.MultisigRedeemScriptType(
            pubkeys=pubs, signatures=[b""] * 15, m=15
        )

        for i in range(15):
            assert (
                btc.get_address(
                    self.client, "Bitcoin", [i], show_display=True, multisig=multisig
                )
                == "3QaKF8zobqcqY8aS6nxCD5ZYdiRfL3RCmU"
            )
