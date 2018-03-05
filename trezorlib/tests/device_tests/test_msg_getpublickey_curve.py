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
import trezorlib.ckd_public as bip32


class TestMsgGetpublickeyCurve(TrezorTest):

    def test_default_curve(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert hexlify(self.client.get_public_node([0x80000000 | 111, 42]).node.public_key).decode() == '02e7fcec053f0df94d88c86447970743e8a1979d242d09338dcf8687a9966f7fbc'
        assert hexlify(self.client.get_public_node([0x80000000 | 111, 0x80000000 | 42]).node.public_key).decode() == '03ce7b690969d773ba9ed212464eb2b534b87b9b8a9383300bddabe1f093f79220'

    def test_secp256k1_curve(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert hexlify(self.client.get_public_node([0x80000000 | 111, 42], ecdsa_curve_name='secp256k1').node.public_key).decode() == '02e7fcec053f0df94d88c86447970743e8a1979d242d09338dcf8687a9966f7fbc'
        assert hexlify(self.client.get_public_node([0x80000000 | 111, 0x80000000 | 42], ecdsa_curve_name='secp256k1').node.public_key).decode() == '03ce7b690969d773ba9ed212464eb2b534b87b9b8a9383300bddabe1f093f79220'

    def test_nist256p1_curve(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert hexlify(self.client.get_public_node([0x80000000 | 111, 42], ecdsa_curve_name='nist256p1').node.public_key).decode() == '02a9ce59b32bd64a70bc52aca96e5d09af65c6b9593ba2a60af8fccfe1437f2129'
        assert hexlify(self.client.get_public_node([0x80000000 | 111, 0x80000000 | 42], ecdsa_curve_name='nist256p1').node.public_key).decode() == '026fe35d8afed67dbf0561a1d32922e8ad0cd0d86effbc82be970cbed7d9bab2c2'

    def test_ed25519_curve(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert hexlify(self.client.get_public_node([0x80000000 | 111, 42], ecdsa_curve_name='ed25519').node.public_key).decode() == '001d9a1e56f69828d44ec96dad345678411976d3ea6d290fe3ae8032c47699ce15'
        assert hexlify(self.client.get_public_node([0x80000000 | 111, 0x80000000 | 42], ecdsa_curve_name='ed25519').node.public_key).decode() == '0069a14b478e508eab6e93303f4e6f5c50b8136627830f2ed5c3a835fc6c0ea2b7'
