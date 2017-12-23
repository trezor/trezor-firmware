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

from .common import *
from trezorlib import messages as proto
from mnemonic import Mnemonic


@pytest.mark.skip_t2
class TestMsgResetDeviceSkipbackup(TrezorTest):

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
        assert isinstance(ret, proto.EntropyRequest)
        internal_entropy = self.client.debug.read_reset_entropy()
        ret = self.client.call_raw(proto.EntropyAck(entropy=external_entropy))
        assert isinstance(ret, proto.Success)

        # Check if device is properly initialized
        resp = self.client.call_raw(proto.Initialize())
        assert resp.initialized is True
        assert resp.needs_backup is True

        # Generate mnemonic locally
        entropy = generate_entropy(strength, internal_entropy, external_entropy)
        expected_mnemonic = Mnemonic('english').to_mnemonic(entropy)

        # start Backup workflow
        ret = self.client.call_raw(proto.BackupDevice())

        mnemonic = []
        for _ in range(strength // 32 * 3):
            assert isinstance(ret, proto.ButtonRequest)
            mnemonic.append(self.client.debug.read_reset_word())
            self.client.debug.press_yes()
            self.client.call_raw(proto.ButtonAck())

        mnemonic = ' '.join(mnemonic)

        # Compare that device generated proper mnemonic for given entropies
        assert mnemonic == expected_mnemonic

        mnemonic = []
        for _ in range(strength // 32 * 3):
            assert isinstance(ret, proto.ButtonRequest)
            mnemonic.append(self.client.debug.read_reset_word())
            self.client.debug.press_yes()
            resp = self.client.call_raw(proto.ButtonAck())

        assert isinstance(resp, proto.Success)

        mnemonic = ' '.join(mnemonic)

        # Compare that second pass printed out the same mnemonic once again
        assert mnemonic == expected_mnemonic

        # start backup again - should fail
        ret = self.client.call_raw(proto.BackupDevice())
        assert isinstance(ret, proto.Failure)

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
        assert isinstance(ret, proto.EntropyRequest)
        ret = self.client.call_raw(proto.EntropyAck(entropy=external_entropy))
        assert isinstance(ret, proto.Success)

        # Check if device is properly initialized
        resp = self.client.call_raw(proto.Initialize())
        assert resp.initialized is True
        assert resp.needs_backup is True

        # start Backup workflow
        ret = self.client.call_raw(proto.BackupDevice())

        # send Initialize -> break workflow
        ret = self.client.call_raw(proto.Initialize())
        assert isinstance(resp, proto.Features)

        # start backup again - should fail
        ret = self.client.call_raw(proto.BackupDevice())
        assert isinstance(ret, proto.Failure)

    def test_initialized_device_backup_fail(self):
        self.setup_mnemonic_nopin_nopassphrase()
        ret = self.client.call_raw(proto.BackupDevice())
        assert isinstance(ret, proto.Failure)
