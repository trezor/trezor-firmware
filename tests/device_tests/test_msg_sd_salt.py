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

from ..common import MNEMONIC12


@pytest.mark.skip_t1
class TestMsgSdsalt:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_sd_salt(self, client):

        # Disabling SD salt should fail
        ret = client.call_raw(proto.SdSalt(operation=proto.SdSaltOperationType.DISABLE))
        assert isinstance(ret, proto.Failure)

        # Enable SD salt
        ret = client.call_raw(proto.SdSalt(operation=proto.SdSaltOperationType.ENABLE))
        assert isinstance(ret, proto.ButtonRequest)

        # Confirm operation
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())
        assert isinstance(ret, proto.Success)

        # Enabling SD salt should fail
        ret = client.call_raw(proto.SdSalt(operation=proto.SdSaltOperationType.ENABLE))
        assert isinstance(ret, proto.Failure)

        # Wipe
        device.wipe(client)
        debuglink.load_device_by_mnemonic(
            client,
            mnemonic=MNEMONIC12,
            pin="",
            passphrase_protection=False,
            label="test",
        )

        # Enable SD salt
        ret = client.call_raw(proto.SdSalt(operation=proto.SdSaltOperationType.ENABLE))
        assert isinstance(ret, proto.ButtonRequest)

        # Confirm operation
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())
        assert isinstance(ret, proto.Success)

        # Regenerate SD salt
        ret = client.call_raw(
            proto.SdSalt(operation=proto.SdSaltOperationType.REGENERATE)
        )
        assert isinstance(ret, proto.ButtonRequest)

        # Confirm operation
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())
        assert isinstance(ret, proto.Success)

        # Disable SD salt
        ret = client.call_raw(proto.SdSalt(operation=proto.SdSaltOperationType.DISABLE))
        assert isinstance(ret, proto.ButtonRequest)

        # Confirm operation
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())
        assert isinstance(ret, proto.Success)

        # Regenerating SD salt should fail
        ret = client.call_raw(
            proto.SdSalt(operation=proto.SdSaltOperationType.REGENERATE)
        )
        assert isinstance(ret, proto.Failure)
