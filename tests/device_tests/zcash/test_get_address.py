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

from trezorlib import zcash
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path


@pytest.mark.skip_t1
def test_get_address(client: Client):
    # Testnet
    address = zcash.get_address(
        client,
        z_address_n=parse_path("m/32h/1h/82h"),
        coin_name="Zcash Testnet",
        diversifier_index=95,
    )
    assert (
        address
        == "utest1w7qxcnjytut5dx9eakmcc7uz6dy2tccrdwd5j7yl5smezt5ehketyge7jpk22m8aka2xuesu6nuldd6gv0g5qcrrxu503wdw8cxev9at"
    )

    address = zcash.get_address(
        client,
        z_address_n=parse_path("m/32h/1h/89h"),
        coin_name="Zcash Testnet",
        diversifier_index=236,
    )
    assert (
        address
        == "utest10559ry4vecyfkhsxs9zx5h4hg9x2zkl627982emgjrxt5xzrgg79hvp8caq9ne6c74wcrtgj9wz2yk43g2hnrhr9x8cny0zuqcplgszd"
    )

    address = zcash.get_address(
        client,
        z_address_n=parse_path("m/32h/1h/12h"),
        coin_name="Zcash Testnet",
        diversifier_index=530,
    )
    assert (
        address
        == "utest1ak77fyqh76cy6xdt9rpn4mr6j6nxldspy7qq97c9gptcnrav5yc5re2ktjc37gjky92zd5p6xl6kjshqhddtj059g5qnt2g74gjch9p5"
    )

    # Mainnet
    address = zcash.get_address(
        client,
        z_address_n=parse_path("m/32h/133h/25h"),
        coin_name="Zcash",
        diversifier_index=496,
    )
    assert (
        address
        == "u12cajwycvxn00274at5mjkdfvk8p3zq8xxfx09lvuc7z29qv39939s5tmlx9xphswdlqkkrhwkjqsyvu7ectfh52gn5r6zlm0yv5nk42m"
    )

    address = zcash.get_address(
        client,
        z_address_n=parse_path("m/32h/133h/65h"),
        coin_name="Zcash",
        diversifier_index=674,
    )
    assert (
        address
        == "u1lah2w9h8fzwlw43nklp8v655h3mf6mnt4gpue0yvrq5g8fhpgvjgqja5lvkkwrzek9tgazhqtv9nzdw0arcmnruakdx3ex5dpgadp5wy"
    )

    address = zcash.get_address(
        client,
        z_address_n=parse_path("m/32h/133h/26h"),
        coin_name="Zcash",
        diversifier_index=89,
    )
    assert (
        address
        == "u1uflw0wtdtu0tcsfj6x85enqamxjygwvhk8g0ljf8exvdzz5e8vh7y79fm655fyxflvtfj8vlksj4wx98hjv827542kqkhh6resas9t3n"
    )
