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

from trezorlib import messages as proto
from mnemonic import Mnemonic


class TestDeviceResetSkipBackup(common.TrezorTest):

    def test_reset_device_skip_backup(self):

        external_entropy = b'zlutoucky kun upel divoke ody' * 2
        strength = 128

        ret = self.client.call_raw(proto.ResetDevice(
            display_random=False,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            language='english',
            label='test',
            skip_backup=True
        ))

        # Provide entropy
        self.assertIsInstance(ret, proto.EntropyRequest)
        internal_entropy = self.client.debug.read_reset_entropy()
        ret = self.client.call_raw(proto.EntropyAck(entropy=external_entropy))
        self.assertIsInstance(ret, proto.Success)

        # Check if device is properly initialized
        resp = self.client.call_raw(proto.Initialize())
        self.assertTrue(resp.initialized)
        self.assertTrue(resp.needs_backup)

        # Generate mnemonic locally
        entropy = common.generate_entropy(strength, internal_entropy, external_entropy)
        expected_mnemonic = Mnemonic('english').to_mnemonic(entropy)

        # start Backup workflow
        ret = self.client.call_raw(proto.BackupDevice())

        mnemonic = []
        for _ in range(strength // 32 * 3):
            self.assertIsInstance(ret, proto.ButtonRequest)
            mnemonic.append(self.client.debug.read_reset_word())
            self.client.debug.press_yes()
            self.client.call_raw(proto.ButtonAck())

        mnemonic = ' '.join(mnemonic)

        # Compare that device generated proper mnemonic for given entropies
        self.assertEqual(mnemonic, expected_mnemonic)

        mnemonic = []
        for _ in range(strength // 32 * 3):
            self.assertIsInstance(ret, proto.ButtonRequest)
            mnemonic.append(self.client.debug.read_reset_word())
            self.client.debug.press_yes()
            resp = self.client.call_raw(proto.ButtonAck())

        self.assertIsInstance(resp, proto.Success)

        mnemonic = ' '.join(mnemonic)

        # Compare that second pass printed out the same mnemonic once again
        self.assertEqual(mnemonic, expected_mnemonic)

        # start backup again - should fail
        ret = self.client.call_raw(proto.BackupDevice())
        self.assertIsInstance(ret, proto.Failure)

    def test_reset_device_skip_backup_break(self):

        external_entropy = b'zlutoucky kun upel divoke ody' * 2
        strength = 128

        ret = self.client.call_raw(proto.ResetDevice(
            display_random=False,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            language='english',
            label='test',
            skip_backup=True
        ))

        # Provide entropy
        self.assertIsInstance(ret, proto.EntropyRequest)
        ret = self.client.call_raw(proto.EntropyAck(entropy=external_entropy))
        self.assertIsInstance(ret, proto.Success)

        # Check if device is properly initialized
        resp = self.client.call_raw(proto.Initialize())
        self.assertTrue(resp.initialized)
        self.assertTrue(resp.needs_backup)

        # start Backup workflow
        ret = self.client.call_raw(proto.BackupDevice())

        # send Initialize -> break workflow
        ret = self.client.call_raw(proto.Initialize())
        self.assertIsInstance(resp, proto.Features)

        # start backup again - should fail
        ret = self.client.call_raw(proto.BackupDevice())
        self.assertIsInstance(ret, proto.Failure)

    def test_initialized_device_backup_fail(self):
        self.setup_mnemonic_nopin_nopassphrase()
        ret = self.client.call_raw(proto.BackupDevice())
        self.assertIsInstance(ret, proto.Failure)
