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

from trezorlib import messages


class TestBasicState(TrezorTest):

    def test_state_uninitialized(self):
        self.client.wipe_device()
        f0 = self.client.call(messages.Initialize())
        f1 = self.client.call(messages.Initialize())
        assert f0.state != f1.state
        f2 = self.client.call(messages.Initialize(state=f1.state))
        assert f1.state == f2.state

    def test_state_initialized(self):
        self.setup_mnemonic_nopin_passphrase()
        f0 = self.client.call(messages.Initialize())
        f1 = self.client.call(messages.Initialize())
        assert f0.state != f1.state
        f2 = self.client.call(messages.Initialize(state=f1.state))
        assert f1.state == f2.state
