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

import pytest

from .common import TrezorTest


@pytest.mark.lisk
@pytest.mark.skip_t1
class TestMsgLiskGetaddress(TrezorTest):

    def test_lisk_getaddress(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert self.client.lisk_get_address([2147483692, 2147483782]) == '1431530009238518937L'
        assert self.client.lisk_get_address([2147483692, 2147483782, 2147483648]) == '17563781916205589679L'
        assert self.client.lisk_get_address([2147483692, 2147483782, 2147483648, 2147483649]) == '1874186517773691964L'
        assert self.client.lisk_get_address([2147483692, 2147483782, 2147484647, 2147484647]) == '16295203558710684671L'
