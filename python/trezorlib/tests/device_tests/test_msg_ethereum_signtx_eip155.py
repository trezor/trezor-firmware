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
from trezorlib.tools import H_

from .common import TrezorTest


@pytest.mark.ethereum
class TestMsgEthereumSigntxChainId(TrezorTest):
    def test_ethereum_signtx_eip155(self):

        # chain_id, nonce, sig_v, sig_r, sig_s, value, gas_limit, data
        VECTORS = [
            (
                3,
                0,
                42,
                "cde31d8ab07d423d5e52aeb148180528ea54974cdb4c5578499c0137ec24d892",
                "41fc58955b3b3e3f3b2aced65e11e8a3cb6339027f943bec3d504d6398b69dd2",
                100000000000000000,
                21000,
                None,
            ),
            (
                3,
                1,
                41,
                "57951fed170f3765dea164d65acd31373799db32ec572e213b1d9a1209956b98",
                "0971f8830c0e2e89919309f217ed2eadb0c63d647e016d220729ce79d27c24a0",
                100000000000000000,
                21000,
                None,
            ),
            (
                3,
                2,
                42,
                "73744f66231690edd9eed2ab3c2b56ec4f6c4b9aabc633ae7f3f4ea94223d52c",
                "7f500afbe2b2b4e4e57f22511e3a42b3596b85cad7fe1eca700cdae1905d3555",
                100000000000000000,
                21004,
                b"\0",
            ),
            (
                3,
                3,
                42,
                "1a4fc1ec5f98bf874d5336aaf1fa9069ce68dc36c3f77e93465c9ac2c8b4b741",
                "13007c9b1df6a0d2f2ffa9d0ebcdec189122a5e781eb64967eb0d6a6def95b7a",
                100000000000000000,
                299732,
                b"ABCDEFGHIJKLMNOP" * 256 + b"!!!",
            ),
            (
                3,
                4,
                42,
                "8da0358d780df542f767d977f99ad034b6d9fa808fe50997141be2a1b93542c0",
                "2dafe1ead8aae1051e6662c5d553b34067bda9c8fa7314ae8693ec61ddfc96d4",
                0,
                21004,
                b"\0",
            ),
            (
                1,
                1,
                38,
                "b72707f0f5a38339c9dd0359720312c739a8ac6554659c7af48456f06ba33374",
                "75a431c046046942f9c1f3305cd08f34302164811c675ac0a0ac0b73cb30a90e",
                0,
                21004,
                b"\0",
            ),
            (
                255,
                1,
                545,
                "529172fb644a6d29b7218fb783f3d666021fc29cc4bf9bffbcfb3b84ab8d6181",
                "30980c6102a12872ef9cd888f2bf90c81bbbdc8878ff7d1d1382f8983b0d0c49",
                0,
                21004,
                b"\0",
            ),
            (
                256,
                1,
                548,
                "db53c05c679bdfdf3ded787ce9607d3f109ae46c87b1dcc9ab34053e5ed0eace",
                "39645dd48118d369b588dbf279f1a8c01051fabf65bf8eaa633c6433ff120cce",
                0,
                21004,
                b"\0",
            ),
            (
                65535,
                1,
                131105,
                "b520fa77767cdf07b6014d4a8fb35eebe5ed7c0edab97132b0dc74e3e1f13ed9",
                "78735b2db4cf95fb651c5c1f5529e60542019e456c6cb7a9f4bd9bbb83418d99",
                0,
                21004,
                b"\0",
            ),
            (
                65536,
                1,
                131107,
                "4b6122ba875b57ce084bd5f08e9ae1944e998726a4056c9b7746432d8f46ba99",
                "6812c2668ac9c9927b69ef7cf9baec54436f7319ccc14f0f664e1e94e6109e06",
                0,
                21004,
                b"\0",
            ),
            (
                16777215,
                1,
                33554465,
                "68a8c6f2336a8e3296f17a307d84a1e6d3ab1383fdcc62611c2e8426f2e2777e",
                "2d4ce900077ab40aac26064945998dbac5a014baadae2d3cb629cdeb9452db61",
                0,
                21004,
                b"\0",
            ),
            (
                16777216,
                1,
                33554468,
                "b6c42c584ef69621a2e5f3e1ab9dad890dbff3c92a599230dd0e394cd29d1c68",
                "497eec05ea52773d0f05e7fdf4f7993b3a06ef958804b39af699ef09ed0f5d7e",
                0,
                21004,
                b"\0",
            ),
            (
                2147483629,
                1,
                4294967294,
                "1a31f886c0bba527e622a731270dc29e62a607ff63558fca38745e5b9a672686",
                "0f3fce8a70598bbb54387cde7e8f957a27e4a816cbc9408717b27d8666222bd9",
                0,
                21004,
                b"\0",
            ),
            (
                2147483630,
                1,
                4294967296,
                "ba6cb6e2ebbac3726db9a3e4a939454009108f6515330e567aeada14ecebe074",
                "2bbfba1154cae32e3e6c6bbf3ce41cba6cc8c6b764245ba6026605506838e690",
                0,
                21004,
                None,
            ),
            (
                2147483631,
                1,
                4294967298,
                "3c743528e9ce315db02e487de93f2b2cfc93421e43f1d519f77a2f05bd2ce190",
                "16c1fec1495fe5da89d1a026f1a575ff354e18ff0fb9d04a6cfb0413267ab2bc",
                100000000000000000,
                21000,
                None,
            ),
            (
                3125659152,
                1,
                6251318340,
                "82cde0c9e1a94c1305791b09e1bcd021a49b036a16d9733acbc1a08bb30f3410",
                "472c8897519ba410b86f80993236d992e18e94d1f59c3d8760d2d7c90914dfc6",
                1,
                21005,
                None,
            ),
            (
                4294967295,
                1,
                8589934625,
                "67788e892fb372bba16823e16d3186f67494d7b1128555248f3661ad87e9d7ef",
                "2faf9f06dfdf23ceca2796cf0d55c88187f199e98a94dfb15722824b244d81a1",
                100000000000000000,
                21000,
                None,
            ),
        ]

        self.setup_mnemonic_allallall()

        for ci, n, sv, sr, ss, v, gl, d in VECTORS:
            sig_v, sig_r, sig_s = ethereum.sign_tx(
                self.client,
                n=[H_(44), H_(60), H_(0), 0, 0],
                nonce=n,
                gas_price=20000000000,
                gas_limit=gl,
                to="0x8eA7a3fccC211ED48b763b4164884DDbcF3b0A98",
                value=v,
                chain_id=ci,
                data=d,
            )
            assert sig_v == sv
            assert sig_r.hex() == sr
            assert sig_s.hex() == ss
