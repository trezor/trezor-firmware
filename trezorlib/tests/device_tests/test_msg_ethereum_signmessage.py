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

from .common import *


@pytest.mark.skip_t2
class TestMsgEthereumSignmessage(TrezorTest):

    def test_sign(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = self.client.ethereum_sign_message([0], 'This is an example of a signed message.')
        assert hexlify(sig.address) == b'cb3864960e8db1a751212c580af27ee8867d688f'
        assert hexlify(sig.signature) == b'95b64a7b3aa492f0cc1668a24097004562cc2b4f0e755e3c0d60dd791b9f9e285f95b618258ff97036b8419d0a0dd1af3751c625b4d248ee6deff84eba21b8ee1c'

    def test_sign_long(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = self.client.ethereum_sign_message([0], 'VeryLongMessage!' * 64)
        assert hexlify(sig.address) == b'cb3864960e8db1a751212c580af27ee8867d688f'
        assert hexlify(sig.signature) == b'70d03c8447b64489e80ae44ce4f1a543e8eb5dd9e9a19c4743ce95fbd9b8234b2d2a16db87cee857f5b474107ad2c0c0c86118f8a33d5df3d98b766be92d71331b'
