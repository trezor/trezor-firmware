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

from trezorlib import messages as proto

from .common import TrezorTest


class TestMsgResetDeviceNobackup(TrezorTest):

    external_entropy = b"zlutoucky kun upel divoke ody" * 2
    strength = 128

    @pytest.mark.setup_client(uninitialized=True)
    def test_reset_device_no_backup(self, client):
        ret = client.call_raw(
            proto.ResetDevice(
                display_random=False,
                strength=self.strength,
                passphrase_protection=False,
                pin_protection=False,
                language="english",
                label="test",
                no_backup=True,
            )
        )

        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Provide entropy
        assert isinstance(ret, proto.EntropyRequest)
        ret = client.call_raw(proto.EntropyAck(entropy=self.external_entropy))
        assert isinstance(ret, proto.Success)

        # Check if device is properly initialized
        ret = client.call_raw(proto.Initialize())
        assert ret.initialized is True
        assert ret.needs_backup is False
        assert ret.unfinished_backup is False
        assert ret.no_backup is True

        # start backup - should fail
        ret = client.call_raw(proto.BackupDevice())
        assert isinstance(ret, proto.Failure)

    @pytest.mark.setup_client(uninitialized=True)
    def test_reset_device_no_backup_show_entropy_fail(self, client):
        ret = client.call_raw(
            proto.ResetDevice(
                display_random=True,
                strength=self.strength,
                passphrase_protection=False,
                pin_protection=False,
                language="english",
                label="test",
                no_backup=True,
            )
        )
        assert isinstance(ret, proto.Failure)
