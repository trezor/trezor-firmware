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

from trezorlib import ethereum
from trezorlib.tools import parse_path

PATH = parse_path("m/44h/60h/0h/0/0")
ADDRESS = "0x73d0385F4d8E00C5e6504C6030F47BF6212736A8"
VECTORS = (  # message, signature
    (
        "This is an example of a signed message.",
        "af4eac50f21acc6daeb0ab036f616f5d19fccade46e47100642b3dfc798c9b740d5873887bdc2f02502c90777a082d10dca113bd1ec29d08108396401421c8cc1b",
    ),
    (
        "VeryLongMessage!" * 64,
        "e9b3648fe10146a7c5c73ae1e42468273b945554b13769be19c3658e5b55c62d7036b56c1e094dc364060b798b120a528f31d91e815d0612c367bf7471519c761c",
    ),
    (
        "MsgLenIs9",
        "495b5b021517cd01cb05f02dfb6a1f79a8d9e4f82e8fb01d44ebf7d1218333f1528b67043ffc25c5b64b1e5a182f5d7d5707fcb639092af708969f90038155a91c",
    ),
    (
        "MsgLenIs10",
        "0c8eb57decbb95d2a783e69d444b3747c49ebcceb14f24287732ba77c39aa5cd2c66f7ec545b8108ef7ce078edac4588c70ab6249fc626114a95606783828f041b",
    ),
    (
        "MsgLenIs11!",
        "5f1ab8940c2137baf69a2b94f55f0f7e53a022b9e363b564744616271eb89b66145055fc9923c6ead63dd784854c742f4f5651c8257d70cbce5a96ce2986dd311c",
    ),
    (
        "This message has length 99" + 73 * "!",
        "f2c3d9c81fe35a6bc68f0ace01bd7209baf11e455e7335903e7ad2879ce5d7bc2199bf8bafc1efe1ff2cfdf2963cd5767911a641c9445cca6f37dc6da72fd1611b",
    ),
    (
        "This message has length 100" + 73 * "!",
        "a6d05d98180246cbd7084f191465d02c4242bc7f856632a2b5b43acd496c46c03a36cc60bfeca6ca98fd210748a3aa68aa7ebba71b39adcad7f88325fc34131a1b",
    ),
    (
        "This message has length 101" + 74 * "!",
        "fa9d60644436f27eb88956a50893e9a47f67c42fb1b57a44bde4c6e127ab777e0c23b234b6ec9327ffd0620daaa514243ebb5a3652a1bac2d720e0f5555b2e071c",
    ),
)


@pytest.mark.altcoin
@pytest.mark.ethereum
@pytest.mark.parametrize("message, signature", VECTORS)
def test_sign(client, message, signature):
    res = ethereum.sign_message(client, PATH, message)
    assert res.address == ADDRESS
    assert res.signature.hex() == signature
