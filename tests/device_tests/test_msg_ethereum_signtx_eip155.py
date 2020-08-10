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

VECTORS_CHAIN_IDS = (  # chain_id, slip44, sig_v, sig_r, sig_s
    # Ethereum
    (
        1,
        60,
        (
            38,
            "6a6349bddb5749bb8b96ce2566a035ef87a09dbf89b5c7e3dfdf9ed725912f24",
            "4ae58ccd3bacee07cdc4a3e8540544fd009c4311af7048122da60f2054c07ee4",
        ),
    ),
    # Ropsten
    (
        3,
        1,
        (
            42,
            "9d49a5c234a134bc56d00a7cf0c208c97d746f002c1fd3609b643eb8ef99d07d",
            "3f064e133624cb59f8103fd5de76c089d8754e3da233a59d2ab2ca47fc306837",
        ),
    ),
    # Rinkeby
    (
        4,
        1,
        (
            43,
            "79a9fd0391f027ed518f3d796a598bf33eef0fb30ef22568a140d674d6b0b76c",
            "408cd459abafcdb7f2e415b269c85a308aad4c53e63c01d3431d3db6ab6292dd",
        ),
    ),
    # ETC
    (
        61,
        61,
        (
            158,
            "6f03621da2fe75877494697b0852c379ea3b2c4ec4f99ab9ce0c8753ebbaf3aa",
            "2b8c8def7534e7bc692ee2975a674a0e31c0dbd9137e53d27dee6b15e121c210",
        ),
    ),
    # EOS Classic
    (
        2018,
        2018,
        (
            4071,
            "2a890f3e4ae40614dd093e0696b99da02bb25ec03cdd3e7c1a77c425b8dc010b",
            "33db0e15ab3d6d02f7c4e0ed39e496c0e5859b998e1258ce8d17a7f254e2c967",
        ),
    ),
    # Auxilium
    (
        28945486,
        344,
        (
            57891008,
            "3298b58680045cfb373b9945f17c468a5c5725c9115c7c18915e8c585c67193f",
            "6bf1c719350150a520d59542815afd8263d7fe7087608051abe7df11dd7fcbec",
        ),
    ),
    # Pirl
    (
        3125659152,
        164,
        (
            6251318340,
            "a876d3cf19f4f6b51fb980aac49e8bd378b88f11adbebc1be33d7b86eb84a054",
            "3bee0e5a07661e78c9c4af49c8a42f4735f80cbb82931607ac35fc78f8d5b113",
        ),
    ),
)


@pytest.mark.altcoin
@pytest.mark.ethereum
@pytest.mark.parametrize("chain_id, slip44, sig", VECTORS_CHAIN_IDS)
def test_chain_ids(client, chain_id, slip44, sig):
    sig_v, sig_r, sig_s = ethereum.sign_tx(
        client,
        n=parse_path(f"m/44h/{slip44}h/0h/0/0"),
        nonce=0,
        gas_price=20000000000,
        gas_limit=21000,
        to="0x8eA7a3fccC211ED48b763b4164884DDbcF3b0A98",
        value=10000000000,
        chain_id=chain_id,
    )
    expected_v = 2 * chain_id + 35
    assert sig_v in (expected_v, expected_v + 1)
    assert (sig_v, sig_r.hex(), sig_s.hex()) == sig


@pytest.mark.altcoin
@pytest.mark.ethereum
def test_with_data(client):
    sig_v, sig_r, sig_s = ethereum.sign_tx(
        client,
        n=parse_path("m/44h/60h/0h/0/0"),
        nonce=0,
        gas_price=20000000000,
        gas_limit=21000,
        to="0x8eA7a3fccC211ED48b763b4164884DDbcF3b0A98",
        value=10000000000,
        chain_id=1,
        data=b"ABCDEFGHIJKLM",
    )
    assert sig_v == 37
    assert (
        sig_r.hex()
        == "c57556e308f49c84adc614042bf443381676fd2797f9512a85dc529f7acb7fa8"
    )
    assert (
        sig_s.hex()
        == "60a82338641fd4a924a6ec31da4aadc0a43ac77d3a021307ec07bb6982ccbe8d"
    )
