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

from trezorlib import debuglink
from trezorlib.ripple import get_public_key
from trezorlib.tools import parse_path

from .common import TrezorTest

CUSTOM_MNEMONIC = (
    "armed bundle pudding lazy strategy impulse where identify "
    "submit weekend physical antenna flight social acoustic absurd "
    "whip snack decide blur unfold fiction pumpkin athlete"
)


@pytest.mark.ripple
@pytest.mark.skip_t1  # T1 support is not planned
class TestMsgRippleGetAddress(TrezorTest):
    def test_ripple_get_public_key(self):
        self.setup_mnemonic_allallall()

        public_key = get_public_key(self.client, parse_path("m/44'/144'/0'/0/0"))
        assert (
            public_key
            == "02131FACD1EAB748D6CDDC492F54B04E8C35658894F4ADD2232EBC5AFE7521DBE4"
        )
        public_key = get_public_key(self.client, parse_path("m/44'/144'/0'/0/1"))
        assert (
            public_key
            == "02C98A3644483E6C500D579F7B7E84BC4E461D7AC923B87ABD0E272D02509D7360"
        )
        public_key = get_public_key(self.client, parse_path("m/44'/144'/1'/0/0"))
        assert (
            public_key
            == "03AD39F736DEBAFB1805AD09B5DF9A6A7F795511430BF75CE4FED6904C1DDF438C"
        )

    def test_ripple_get_public_key_other(self):
        debuglink.load_device_by_mnemonic(
            self.client,
            mnemonic=CUSTOM_MNEMONIC,
            pin="",
            passphrase_protection=False,
            label="test",
            language="english",
        )

        public_key = get_public_key(self.client, parse_path("m/44'/144'/0'/0/0"))
        assert (
            public_key
            == "032E6A7359B17D56DBFB2B627F82D38E374DF622D8E15806CF607BBD44057E9C3A"
        )
        public_key = get_public_key(self.client, parse_path("m/44'/144'/0'/0/1"))
        assert (
            public_key
            == "03C555B80639FF96C0935246D527F313C8522ACF70643CA9449006E5CFBF2B66F3"
        )
