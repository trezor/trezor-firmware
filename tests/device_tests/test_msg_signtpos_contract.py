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

from ..common import MNEMONIC12


class TestMsgSigntposContract:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_sign_stakenet_0(self, client):
        sig = btc.sign_tpos_contract(
            client,
            "Stakenet",
            [0],
            "8aa2b43bb74ca579c08da494763aa8c0d87a6727893a6c7b88ee2e56e3b1c1f6:0",
        )
        assert sig.address == "Xe2cLLPxqahT3XkkuuPJrAXhsved39jeqa"
        assert (
            sig.signature.hex()
            == "20d04dca258c81c46f24eb1124bfe192205ff06b19b1167fd8249c932994514feb7e02760505aad543dbd72921ace785565682c1d900e29284cb21f0b8daad6d49"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_sign_stakenet_1(self, client):
        sig = btc.sign_tpos_contract(
            client,
            "Stakenet",
            [1],
            "483bdb594fe347052cb56c60000fba593ef7dee8bf3f069e616fbdf8353e38ae:0",
        )
        assert sig.address == "Xat9wgxXaJMaJEWWMZCG4fh5B9utBXcpba"
        assert (
            sig.signature.hex()
            == "20b542168ae416b86a0ed0d4646e0ba9ca7f2e59fa7de986bd8de21e0edba22c654935a638562c68aea42e1c695fd581740bdf34d0a62b2719bd27d145a77dd832"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_sign_stakenet_2(self, client):
        sig = btc.sign_tpos_contract(
            client,
            "Stakenet",
            [2],
            "483bdb594fe347052cb56c60000fba593ef7dee8bf3f069e616fbdf8353e38ae:99",
        )
        assert sig.address == "XerUzxYGG5YZxsuihGcAYMDYYDPT3XWkf6"
        assert (
            sig.signature.hex()
            == "209e127bb228d7ffeb19696076bfc64165e27dde13ee20c2c93621d16bf95a9a2f47522021203fefc4ecf86724acfe65324e9ec2444246536f5b34c89a09415f9f"
        )
