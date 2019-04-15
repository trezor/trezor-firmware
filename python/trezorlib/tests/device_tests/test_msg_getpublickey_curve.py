# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from trezorlib import btc
from trezorlib.tools import H_, CallException

from .common import TrezorTest


class TestMsgGetpublickeyCurve(TrezorTest):
    def test_default_curve(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert (
            btc.get_public_node(self.client, [H_(111), 42]).node.public_key.hex()
            == "02e7fcec053f0df94d88c86447970743e8a1979d242d09338dcf8687a9966f7fbc"
        )
        assert (
            btc.get_public_node(self.client, [H_(111), H_(42)]).node.public_key.hex()
            == "03ce7b690969d773ba9ed212464eb2b534b87b9b8a9383300bddabe1f093f79220"
        )

    def test_secp256k1_curve(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert (
            btc.get_public_node(
                self.client, [H_(111), 42], ecdsa_curve_name="secp256k1"
            ).node.public_key.hex()
            == "02e7fcec053f0df94d88c86447970743e8a1979d242d09338dcf8687a9966f7fbc"
        )
        assert (
            btc.get_public_node(
                self.client, [H_(111), H_(42)], ecdsa_curve_name="secp256k1"
            ).node.public_key.hex()
            == "03ce7b690969d773ba9ed212464eb2b534b87b9b8a9383300bddabe1f093f79220"
        )

    def test_nist256p1_curve(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert (
            btc.get_public_node(
                self.client, [H_(111), 42], ecdsa_curve_name="nist256p1"
            ).node.public_key.hex()
            == "02a9ce59b32bd64a70bc52aca96e5d09af65c6b9593ba2a60af8fccfe1437f2129"
        )
        assert (
            btc.get_public_node(
                self.client, [H_(111), H_(42)], ecdsa_curve_name="nist256p1"
            ).node.public_key.hex()
            == "026fe35d8afed67dbf0561a1d32922e8ad0cd0d86effbc82be970cbed7d9bab2c2"
        )

    def test_ed25519_curve(self):
        self.setup_mnemonic_nopin_nopassphrase()
        # ed25519 curve does not support public derivation, so test only private derivation paths
        assert (
            btc.get_public_node(
                self.client, [H_(111), H_(42)], ecdsa_curve_name="ed25519"
            ).node.public_key.hex()
            == "0069a14b478e508eab6e93303f4e6f5c50b8136627830f2ed5c3a835fc6c0ea2b7"
        )
        assert (
            btc.get_public_node(
                self.client, [H_(111), H_(65535)], ecdsa_curve_name="ed25519"
            ).node.public_key.hex()
            == "00514f73a05184458611b14c348fee4fd988d36cf3aee7207737861bac611de991"
        )
        # test failure when using public derivation
        with pytest.raises(CallException):
            btc.get_public_node(self.client, [H_(111), 42], ecdsa_curve_name="ed25519")
