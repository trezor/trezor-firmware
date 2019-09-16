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

from trezorlib import device, messages as proto


class TestMsgWipedevice:
    @pytest.mark.setup_client(pin=True, passphrase=True)
    def test_wipe_device(self, client):
        features = client.call_raw(proto.Initialize())

        assert features.initialized is True
        assert features.pin_protection is True
        assert features.passphrase_protection is True
        device_id = features.device_id

        device.wipe(client)
        features = client.call_raw(proto.Initialize())

        assert features.initialized is False
        assert features.pin_protection is False
        assert features.passphrase_protection is False
        assert features.device_id != device_id
