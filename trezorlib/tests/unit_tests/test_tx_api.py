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

import os

from trezorlib import coins, tx_api

from ..support.tx_cache import tx_cache

TxApiBitcoin = coins.tx_api["Bitcoin"]
TxApiTestnet = tx_cache("Testnet", allow_fetch=False)
TxApiZencash = coins.tx_api["Zencash"]

tests_dir = os.path.dirname(os.path.abspath(__file__))


def test_tx_api_gettx():
    tx_api.cache_dir = os.path.join(tests_dir, "../txcache")

    TxApiBitcoin.get_tx(
        "39a29e954977662ab3879c66fb251ef753e0912223a83d1dcb009111d28265e5"
    )
    TxApiBitcoin.get_tx(
        "54aa5680dea781f45ebb536e53dffc526d68c0eb5c00547e323b2c32382dfba3"
    )
    TxApiBitcoin.get_tx(
        "58497a7757224d1ff1941488d23087071103e5bf855f4c1c44e5c8d9d82ca46e"
    )
    TxApiBitcoin.get_tx(
        "6189e3febb5a21cee8b725aa1ef04ffce7e609448446d3a8d6f483c634ef5315"
    )
    TxApiBitcoin.get_tx(
        "a6e2829d089cee47e481b1a753a53081b40738cc87e38f1d9b23ab57d9ad4396"
    )
    TxApiBitcoin.get_tx(
        "c6091adf4c0c23982a35899a6e58ae11e703eacd7954f588ed4b9cdefc4dba52"
    )
    TxApiBitcoin.get_tx(
        "c63e24ed820c5851b60c54613fbc4bcb37df6cd49b4c96143e99580a472f79fb"
    )
    TxApiBitcoin.get_tx(
        "c6be22d34946593bcad1d2b013e12f74159e69574ffea21581dad115572e031c"
    )
    TxApiBitcoin.get_tx(
        "d1d08ea63255af4ad16b098e9885a252632086fa6be53301521d05253ce8a73d"
    )
    TxApiBitcoin.get_tx(
        "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
    )
    TxApiBitcoin.get_tx(
        "e4bc1ae5e5007a08f2b3926fe11c66612e8f73c6b00c69c7027213b84d259be3"
    )

    TxApiTestnet.get_tx(
        "6f90f3c7cbec2258b0971056ef3fe34128dbde30daa9c0639a898f9977299d54"
    )
    TxApiTestnet.get_tx(
        "d6da21677d7cca5f42fbc7631d062c9ae918a0254f7c6c22de8e8cb7fd5b8236"
    )


def test_tx_api_current_block():
    height = TxApiZencash.current_height()
    assert height > 347041


def test_tx_api_get_block_hash():
    hash = TxApiZencash.get_block_hash(110000)
    assert (
        hash.hex() == "000000003f5d6ba1385c6cd2d4f836dfc5adf7f98834309ad67e26faef462454"
    )
