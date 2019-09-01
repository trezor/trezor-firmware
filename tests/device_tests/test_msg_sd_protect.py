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

from trezorlib import debuglink, device, messages as proto
from trezorlib.exceptions import TrezorFailure

from ..common import MNEMONIC12


@pytest.mark.skip_t1
class TestMsgSdProtect:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_sd_protect(self, client):

        # Disabling SD protection should fail
        with pytest.raises(TrezorFailure):
            device.sd_protect(client, proto.SdProtectOperationType.DISABLE)

        # Enable SD protection
        device.sd_protect(client, proto.SdProtectOperationType.ENABLE)

        # Enabling SD protection should fail
        with pytest.raises(TrezorFailure):
            device.sd_protect(client, proto.SdProtectOperationType.ENABLE)

        # Wipe
        device.wipe(client)
        debuglink.load_device_by_mnemonic(
            client,
            mnemonic=MNEMONIC12,
            pin="",
            passphrase_protection=False,
            label="test",
        )

        # Enable SD protection
        device.sd_protect(client, proto.SdProtectOperationType.ENABLE)

        # Refresh SD protection
        device.sd_protect(client, proto.SdProtectOperationType.REFRESH)

        # Disable SD protection
        device.sd_protect(client, proto.SdProtectOperationType.DISABLE)

        # Refreshing SD protection should fail
        with pytest.raises(TrezorFailure):
            device.sd_protect(client, proto.SdProtectOperationType.REFRESH)
