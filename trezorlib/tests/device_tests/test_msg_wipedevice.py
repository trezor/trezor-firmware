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


class TestMsgWipedevice(TrezorTest):

    def test_wipe_device(self):
        self.setup_mnemonic_pin_passphrase()
        features = self.client.call_raw(proto.Initialize())

        assert features.initialized is True
        assert features.pin_protection is True
        assert features.passphrase_protection is True
        device_id = features.device_id

        self.client.wipe_device()
        features = self.client.call_raw(proto.Initialize())

        assert features.initialized is False
        assert features.pin_protection is False
        assert features.passphrase_protection is False
        assert features.device_id != device_id
