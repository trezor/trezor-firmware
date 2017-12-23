# This file is part of the TREZOR project.
#
# Copyright (C) 2017 Saleem Rashid <trezor@saleemrashid.com>
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


@pytest.mark.skip_t2
class TestMsgNEMGetaddress(TrezorTest):

    def test_nem_getaddress(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert self.client.nem_get_address(self.client.expand_path("m/44'/1'/0'/0'/0'"), 0x68) == "NB3JCHVARQNGDS3UVGAJPTFE22UQFGMCQGHUBWQN"
        assert self.client.nem_get_address(self.client.expand_path("m/44'/1'/0'/0'/0'"), 0x98) == "TB3JCHVARQNGDS3UVGAJPTFE22UQFGMCQHSBNBMF"
