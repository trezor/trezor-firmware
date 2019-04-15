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

import pytest
from mnemonic import Mnemonic

from trezorlib import messages as proto

from .common import TrezorTest, generate_entropy


@pytest.mark.skip_t2
class TestMsgResetDeviceSkipbackup(TrezorTest):

    external_entropy = b"zlutoucky kun upel divoke ody" * 2
    strength = 128

    def test_reset_device_skip_backup(self):

        ret = self.client.call_raw(
            proto.ResetDevice(
                display_random=False,
                strength=self.strength,
                passphrase_protection=False,
                pin_protection=False,
                language="english",
                label="test",
                skip_backup=True,
            )
        )

        assert isinstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Provide entropy
        assert isinstance(ret, proto.EntropyRequest)
        internal_entropy = self.client.debug.read_reset_entropy()
        ret = self.client.call_raw(proto.EntropyAck(entropy=self.external_entropy))
        assert isinstance(ret, proto.Success)

        # Check if device is properly initialized
        ret = self.client.call_raw(proto.Initialize())
        assert ret.initialized is True
        assert ret.needs_backup is True
        assert ret.unfinished_backup is False
        assert ret.no_backup is False

        # Generate mnemonic locally
        entropy = generate_entropy(
            self.strength, internal_entropy, self.external_entropy
        )
        expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

        # start Backup workflow
        ret = self.client.call_raw(proto.BackupDevice())

        mnemonic = []
        for _ in range(self.strength // 32 * 3):
            assert isinstance(ret, proto.ButtonRequest)
            mnemonic.append(self.client.debug.read_reset_word())
            self.client.debug.press_yes()
            self.client.call_raw(proto.ButtonAck())

        mnemonic = " ".join(mnemonic)

        # Compare that device generated proper mnemonic for given entropies
        assert mnemonic == expected_mnemonic

        mnemonic = []
        for _ in range(self.strength // 32 * 3):
            assert isinstance(ret, proto.ButtonRequest)
            mnemonic.append(self.client.debug.read_reset_word())
            self.client.debug.press_yes()
            ret = self.client.call_raw(proto.ButtonAck())

        assert isinstance(ret, proto.Success)

        mnemonic = " ".join(mnemonic)

        # Compare that second pass printed out the same mnemonic once again
        assert mnemonic == expected_mnemonic

        # start backup again - should fail
        ret = self.client.call_raw(proto.BackupDevice())
        assert isinstance(ret, proto.Failure)

    def test_reset_device_skip_backup_break(self):

        ret = self.client.call_raw(
            proto.ResetDevice(
                display_random=False,
                strength=self.strength,
                passphrase_protection=False,
                pin_protection=False,
                language="english",
                label="test",
                skip_backup=True,
            )
        )

        assert isinstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Provide entropy
        assert isinstance(ret, proto.EntropyRequest)
        ret = self.client.call_raw(proto.EntropyAck(entropy=self.external_entropy))
        assert isinstance(ret, proto.Success)

        # Check if device is properly initialized
        ret = self.client.call_raw(proto.Initialize())
        assert ret.initialized is True
        assert ret.needs_backup is True
        assert ret.unfinished_backup is False
        assert ret.no_backup is False

        # start Backup workflow
        ret = self.client.call_raw(proto.BackupDevice())

        # send Initialize -> break workflow
        ret = self.client.call_raw(proto.Initialize())
        assert isinstance(ret, proto.Features)
        assert ret.initialized is True
        assert ret.needs_backup is False
        assert ret.unfinished_backup is True
        assert ret.no_backup is False

        # start backup again - should fail
        ret = self.client.call_raw(proto.BackupDevice())
        assert isinstance(ret, proto.Failure)

        # read Features again
        ret = self.client.call_raw(proto.Initialize())
        assert isinstance(ret, proto.Features)
        assert ret.initialized is True
        assert ret.needs_backup is False
        assert ret.unfinished_backup is True
        assert ret.no_backup is False

    def test_initialized_device_backup_fail(self):
        self.setup_mnemonic_nopin_nopassphrase()
        ret = self.client.call_raw(proto.BackupDevice())
        assert isinstance(ret, proto.Failure)

    def test_reset_device_skip_backup_show_entropy_fail(self):
        ret = self.client.call_raw(
            proto.ResetDevice(
                display_random=True,
                strength=self.strength,
                passphrase_protection=False,
                pin_protection=False,
                language="english",
                label="test",
                skip_backup=True,
            )
        )
        assert isinstance(ret, proto.Failure)
