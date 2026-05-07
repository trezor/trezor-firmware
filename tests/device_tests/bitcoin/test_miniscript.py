# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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
from trezorlib.debuglink import DebugSession as Session

TPUBS = [
    "tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg",
    "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
]

pytestmark = [pytest.mark.miniscript]

DATA = [
    (0, 0, "tb1qwr00r4x9a2ycm7fn48c7kqm6kpsp56ydwx482ns5c3wxmrwqwu2stjh6cc"),
    (0, 1, "tb1qzvr7ptes6kq2ee0745a7h2n639etfz43nsz9d2jn8u6wz8egx0hqnr5pza"),
    (0, 2, "tb1qerjma9tcyn6qh5yt7wdqqm3q8sz7ft6dn7pratjclzc8pha27rcsgjn0sp"),
    (0, 3, "tb1qc6zh83pdaj64tkmvu5969falc95s7sgs6yku5nh9asspzfmtq8cq7yxr2a"),
    (1, 0, "tb1q5f45hdwm06sf9wa20pcwa5rr9xn99m4yfpzdg406044nl9jhadps2ghwl5"),
    (1, 1, "tb1qk47jne78xqrzxwj5wc8l3qypneh96jumw56lkp50akhqpw5jmr6qwxdctf"),
    (1, 2, "tb1q68hg7scyjs20dndpdl7crr3kue0g8a5pkvktwlnwk4ygheazyfzqnhy9gm"),
]

VECTORS = (  # coin, path, script_type, address
    pytest.param(
        "Testnet",
        "wsh(or_d(pk({0}/<0;1>/*),and_v(v:pkh({1}/<0;1>/*),older(1))))".format(*TPUBS),
        [change, index],
        address,
        id=f'Liana-{"internal" if change else "external"}-{index}',
    )
    for change, index, address in DATA
)


@pytest.mark.parametrize("coin, miniscript, n, address", VECTORS)
def test_miniscript_get_address(
    session: Session,
    coin: str,
    miniscript: str,
    n: list[int],
    address: str,
):
    assert (
        btc.get_address(
            session,
            coin,
            n=n,
            miniscript=miniscript,
        )
        == address
    )
