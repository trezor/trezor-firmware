# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import common
import trezorlib.ckd_public as bip32
from trezorlib import messages as proto


class TestMsgGetaddress(common.TrezorTest):

    def test_show(self):
        self.setup_mnemonic_nopin_nopassphrase()
        self.assertEqual(self.client.get_address('Bitcoin', [1], show_display=True), '1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb')
        self.assertEqual(self.client.get_address('Bitcoin', [2], show_display=True), '15AeAhtNJNKyowK8qPHwgpXkhsokzLtUpG')
        self.assertEqual(self.client.get_address('Bitcoin', [3], show_display=True), '1CmzyJp9w3NafXMSEFH4SLYUPAVCSUrrJ5')

    def test_show_multisig_3(self):
        self.setup_mnemonic_nopin_nopassphrase()

        node = bip32.deserialize('xpub661MyMwAqRbcF1zGijBb2K6x9YiJPh58xpcCeLvTxMX6spkY3PcpJ4ABcCyWfskq5DDxM3e6Ez5ePCqG5bnPUXR4wL8TZWyoDaUdiWW7bKy')
        multisig = proto.MultisigRedeemScriptType(
            pubkeys=[
                proto.HDNodePathType(node=node, address_n=[1]),
                proto.HDNodePathType(node=node, address_n=[2]),
                proto.HDNodePathType(node=node, address_n=[3])
            ],
            signatures=[b'', b'', b''],
            m=2,
        )

        for i in [1, 2, 3]:
            self.assertEqual(self.client.get_address('Bitcoin', [i], show_display=True, multisig=multisig), '3E7GDtuHqnqPmDgwH59pVC7AvySiSkbibz')

    def test_show_multisig_15(self):
        self.setup_mnemonic_nopin_nopassphrase()

        node = bip32.deserialize('xpub661MyMwAqRbcF1zGijBb2K6x9YiJPh58xpcCeLvTxMX6spkY3PcpJ4ABcCyWfskq5DDxM3e6Ez5ePCqG5bnPUXR4wL8TZWyoDaUdiWW7bKy')

        pubs = []
        for x in range(15):
            pubs.append(proto.HDNodePathType(node=node, address_n=[x]))

        multisig = proto.MultisigRedeemScriptType(
            pubkeys=pubs,
            signatures=[b''] * 15,
            m=15,
        )

        for i in range(15):
            self.assertEqual(self.client.get_address('Bitcoin', [i], show_display=True, multisig=multisig), '3QaKF8zobqcqY8aS6nxCD5ZYdiRfL3RCmU')
