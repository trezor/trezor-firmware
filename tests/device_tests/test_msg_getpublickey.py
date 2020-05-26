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

from trezorlib import btc, messages
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from .. import bip32

pytestmark = pytest.mark.skip_ui

VECTORS_BITCOIN = (  # coin_name, xpub_magic, path, xpub
    (
        "Bitcoin",
        0x0488B21E,
        parse_path("m/44h/0h/0h"),
        "xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy",
    ),
    (
        "Bitcoin",
        0x0488B21E,
        parse_path("m/44h/0h/10h"),
        "xpub6BiVtCpG9fQQR6cSuFeDaSvCDgNvNme499JUGX4RHDiZVWwZy9NwNieWKXHLe8XRbdrEmY87aqztBCbRJkXWV7VJB96XBT5cpkqYMHwvLWB",
    ),
    (
        "Bitcoin",
        0x0488B21E,
        parse_path("m/44h/0h/0h/0/0"),
        "xpub6FVDRC1jiWNTuT3embehwSZ1buxRDyZGbTakVCkBr6w2LwpERmYqXyvtrLeJX9hqzLaucS3qJXGekeFsSVCELkbgepp7FVGeH5BYekEgT9x",
    ),
    (
        "Bitcoin",
        0x0488B21E,
        parse_path("m/44h/0h/10h/1/100"),
        "xpub6GhTNegKCjTqjYS4HNkPhXHXHNZV2cPC38N7HbpUKexXXuTkjKPnijqKTB7yXidP4JtTUWTuWPTt6P55xi91NPgUp51BnqYzYdNhho4y5j8",
    ),
    (
        "Testnet",
        0x043587CF,
        parse_path("m/44h/1h/0h"),
        "tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkkfHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U",
    ),
    (
        "Testnet",
        0x043587CF,
        parse_path("m/44h/1h/0h/0/0"),
        "tpubDGwNSs8z8jZU2EcUiubR4frGvKqddvLBqCDNknnWhmoUd6EHrRWrqXmDaWBNddWzM5Yqh4e4TUYFK9hGCEnSrMKgV6cthRhArfZpwzihdw7",
    ),
    (  # PSBT master fingerprint retrieval
        "Bitcoin",
        0x0488B21E,
        parse_path("m/0h"),
        "xpub68Zyu13qjcQvJXTsnmhH2h2TyPiXAama5bTU8u9iRXyYtS9X9yWvSKij6YGt7JJ2nr5rSGi4KLUW5Z8bTKHqXhbLwqb7smG3Y8j2wy4rmf3",
    ),
    pytest.param(
        "Litecoin",
        0x019DA462,
        parse_path("m/44h/2h/0h"),
        "Ltub2Y8PyEMWQVgiX4L4gVzU8PakBTQ2WBxFdS6tJARQeasUUfXmBut2jGShnQyD3jgyBf7mmvs5jPNgmgXad5J6M8a8FiZK78dbT21fYtTAC9a",
        marks=pytest.mark.altcoin,
    ),
    pytest.param(
        "Litecoin",
        0x019DA462,
        parse_path("m/44h/2h/10h"),
        "Ltub2Y8PyEMWQVgiy8Zio1XrKWkGL6ZmCZB9W5ShbvbzZ14irCrAb62YEoMafTAM5a2A6x6XNcyDdCNW7NVgES9jtQqyUZcBUFTimS7VVJ8tbpE",
        marks=pytest.mark.altcoin,
    ),
    pytest.param(
        "Litecoin",
        0x019DA462,
        parse_path("m/44h/2h/0h/0/0"),
        "Ltub2dTvwC4v7GNeR6UEaywQ6j72wHi4dwRo3oDDzvXAwb4CrXVQEUTbxC4hEfULiKByiUMEmYLhuMo1YMYmBBjKJ8kyk9ia5gZaVNWq5rVLom4",
        marks=pytest.mark.altcoin,
    ),
    pytest.param(
        "Litecoin",
        0x019DA462,
        parse_path("m/44h/2h/10h/1/100"),
        "Ltub2dcb6Nghj3kwaC2g3TtPgFzMSm7LXfe4mijFYsvEtxXu18vicTB4kYc9z6jGVMpdYhMScNhVY1naQYALnM2x4fvaGzAAGgcuZ89nFyyLhiK",
        marks=pytest.mark.altcoin,
    ),
)

VECTORS_INVALID = (  # coin_name, path
    ("Bitcoin", parse_path("m/44h/1h/0h")),  # Testnet path on Bitcoin
    ("Testnet", parse_path("m/44h/0h/0h")),  # Bitcoin path on Testnet
    ("Bitcoin", parse_path("m/40h/0h/0h")),  # Unknown purpose
    ("Bitcoin", parse_path("m/13h/0h/0h")),  # SLIP-13 path
    # Bitcoin path on Litecoin
    pytest.param("Litecoin", parse_path("m/44h/0h/0h"), marks=pytest.mark.altcoin),
    # Segwit path on Bitcoin Cash
    pytest.param("Bcash", parse_path("m/84h/145h/0h"), marks=pytest.mark.altcoin),
)


@pytest.mark.parametrize("coin_name, xpub_magic, path, xpub", VECTORS_BITCOIN)
def test_get_public_node(client, coin_name, xpub_magic, path, xpub):
    res = btc.get_public_node(client, path, coin_name=coin_name)
    assert res.xpub == xpub
    assert bip32.serialize(res.node, xpub_magic) == xpub


@pytest.mark.xfail(reason="Currently path validation on get_public_node is disabled.")
@pytest.mark.parametrize("coin_name, path", VECTORS_INVALID)
def test_invalid_path(client, coin_name, path):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_public_node(client, path, coin_name=coin_name)


VECTORS_SCRIPT_TYPES = (  # script_type, xpub
    (
        None,
        "xpub6BiVtCp7ozsRo7kaoYNrCNAVJwPYTQHjoXFD3YS797S55Y42sm2raxPrXQWAJodn7aXnHJdhz433ZJDhyUztHW55WatHeoYUVqui8cYNX8y",
    ),
    (
        messages.InputScriptType.SPENDADDRESS,
        "xpub6BiVtCp7ozsRo7kaoYNrCNAVJwPYTQHjoXFD3YS797S55Y42sm2raxPrXQWAJodn7aXnHJdhz433ZJDhyUztHW55WatHeoYUVqui8cYNX8y",
    ),
    (
        messages.InputScriptType.SPENDP2SHWITNESS,
        "ypub6WYmBsV2xgQueQwhduAUQTFzUuXzQ2HEidmRpwKzX7ox8dsG8RCRD23zYcTkJiHhXDeb2nEGSiPbSaqGhBQu5jkgNvaiEiMxmZyMXEvfNco",
    ),
    (
        messages.InputScriptType.SPENDWITNESS,
        "zpub6qP2VY9x7MxPVi8pUFx6cYMVesgSLeGjdkHecLDsu8BqBjgVP5Myq5i8ZpRLJcwcvrmPnFppuNk9KsSqQspusySHFGH8pdBT3J2zujqcVuz",
    ),
)


@pytest.mark.parametrize("script_type, xpub", VECTORS_SCRIPT_TYPES)
def test_script_type(client, script_type, xpub):
    path = parse_path("m/44h/0h/0")
    res = btc.get_public_node(
        client, path, coin_name="Bitcoin", script_type=script_type
    )
    assert res.xpub == xpub
