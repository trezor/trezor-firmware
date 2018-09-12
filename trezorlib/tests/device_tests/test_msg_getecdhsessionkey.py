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

from trezorlib import messages as proto, misc

from .common import TrezorTest


class TestMsgGetECDHSessionKey(TrezorTest):
    def test_ecdh(self):
        self.setup_mnemonic_nopin_nopassphrase()

        # URI  : gpg://Satoshi Nakamoto <satoshi@bitcoin.org>
        identity = proto.IdentityType(
            proto="gpg",
            user="",
            host="Satoshi Nakamoto <satoshi@bitcoin.org>",
            port="",
            path="",
            index=0,
        )

        peer_public_key = bytes.fromhex(
            "0407f2c6e5becf3213c1d07df0cfbe8e39f70a8c643df7575e5c56859ec52c45ca950499c019719dae0fda04248d851e52cf9d66eeb211d89a77be40de22b6c89d"
        )
        result = misc.get_ecdh_session_key(
            self.client,
            identity=identity,
            peer_public_key=peer_public_key,
            ecdsa_curve_name="secp256k1",
        )
        assert (
            result.session_key.hex()
            == "0495e5d8c9e5cc09e7cf4908774f52decb381ce97f2fc9ba56e959c13f03f9f47a03dd151cbc908bc1db84d46e2c33e7bbb9daddc800f985244c924fd64adf6647"
        )

        peer_public_key = bytes.fromhex(
            "04811a6c2bd2a547d0dd84747297fec47719e7c3f9b0024f027c2b237be99aac39a9230acbd163d0cb1524a0f5ea4bfed6058cec6f18368f72a12aa0c4d083ff64"
        )
        result = misc.get_ecdh_session_key(
            self.client,
            identity=identity,
            peer_public_key=peer_public_key,
            ecdsa_curve_name="nist256p1",
        )
        assert (
            result.session_key.hex()
            == "046d1f5c48af2cf2c57076ac2c9d7808db2086f614cb7b8107119ff2c6270cd209749809efe0196f01a0cc633788cef1f4a2bd650c99570d06962f923fca6d8fdf"
        )

        peer_public_key = bytes.fromhex(
            "40a8cf4b6a64c4314e80f15a8ea55812bd735fbb365936a48b2d78807b575fa17a"
        )
        result = misc.get_ecdh_session_key(
            self.client,
            identity=identity,
            peer_public_key=peer_public_key,
            ecdsa_curve_name="curve25519",
        )
        assert (
            result.session_key.hex()
            == "04e24516669e0b7d3d72e5129fddd07b6644c30915f5c8b7f1f62324afb3624311"
        )
