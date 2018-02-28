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


class TestBasic(TrezorTest):

    def test_features(self):
        f0 = self.client.features
        f1 = self.client.call(messages.Initialize())
        assert f0 == f1

    def test_ping(self):
        ping = self.client.call(messages.Ping(message='ahoj!'))
        assert ping == messages.Success(message='ahoj!')

    def test_device_id_same(self):
        id1 = self.client.get_device_id()
        self.client.init_device()
        id2 = self.client.get_device_id()

        # ID must be at least 12 characters
        assert len(id1) >= 12

        # Every resulf of UUID must be the same
        assert id1 == id2

    def test_device_id_different(self):
        id1 = self.client.get_device_id()
        self.client.wipe_device()
        id2 = self.client.get_device_id()

        # Device ID must be fresh after every reset
        assert id1 != id2
