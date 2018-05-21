# This file is part of the TREZOR project.
#
# Copyright (C) 2016-2017 Pavol Rusnak <stick@satoshilabs.com>
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

from binascii import hexlify
import pytest

from .common import TrezorTest


@pytest.mark.lisk
@pytest.mark.xfail  # drop when trezor-core PR #90 is merged
@pytest.mark.skip_t1
class TestMsgLiskSignmessage(TrezorTest):

    def test_sign(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = self.client.lisk_sign_message([2147483692, 2147483782, 2147483648, 2147483648], 'This is an example of a signed message.')
        assert sig.address == '7623396847864198749L'
        assert hexlify(sig.signature) == b'af1d384cce25354b5af129662caed6f3514c6f1f6a206662d301fd56aa5549aa23c3f82009f213a7a4d9297015c2e5b06584273df7c42d78b4e531fe4d4fc80e'

    def test_sign_long(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = self.client.lisk_sign_message([2147483692, 2147483782, 2147483648], 'VeryLongMessage!' * 64)
        assert sig.address == '17563781916205589679L'
        print(hexlify(sig.signature))
        assert hexlify(sig.signature) == b'a675152c2af34e85dbd75740681efb7d67bf910561d6c9d1e075be2f99d9bc544d62c52f6619756b0e329a2f2d82756ced53b4261a028fcee0d37d7e641ef404'
