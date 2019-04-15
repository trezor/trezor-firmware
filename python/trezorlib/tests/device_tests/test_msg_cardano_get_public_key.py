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

from trezorlib.cardano import get_public_key
from trezorlib.tools import parse_path

from .common import TrezorTest


@pytest.mark.cardano
@pytest.mark.skip_t1  # T1 support is not planned
class TestMsgCardanoGetPublicKey(TrezorTest):
    @pytest.mark.parametrize(
        "path,public_key,chain_code",
        [
            (
                "m/44'/1815'/0'",
                "c0fce1839f1a84c4e770293ac2f5e0875141b29017b7f56ab135352d00ad6966",
                "07faa161c9f5464315d2855f70fdf1431d5fa39eb838767bf17b69772137452f",
            ),
            (
                "m/44'/1815'/1'",
                "ea5dde31b9f551e08a5b6b2f98b8c42c726f726c9ce0a7072102ead53bd8f21e",
                "70f131bb799fd659c997221ad8cae7dcce4e8da701f8101cf15307fd3a3712a1",
            ),
            (
                "m/44'/1815'/2'",
                "076338cee5ab3dae19f06ccaa80e3d4428cf0e1bdc04243e41bba7be63a90da7",
                "5dcdf129f6f2d108292e615c4b67a1fc41a64e6a96130f5c981e5e8e046a6cd7",
            ),
            (
                "m/44'/1815'/3'",
                "5f769380dc6fd17a4e0f2d23aa359442a712e5e96d7838ebb91eb020003cccc3",
                "1197ea234f528987cbac9817ebc31344395b837a3bb7c2332f87e095e70550a5",
            ),
        ],
    )
    def test_cardano_get_public_key(self, path, public_key, chain_code):
        self.setup_mnemonic_allallall()

        key = get_public_key(self.client, parse_path(path))

        assert key.node.public_key.hex() == public_key
        assert key.node.chain_code.hex() == chain_code
        assert key.xpub == public_key + chain_code
