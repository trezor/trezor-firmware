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

from ..common import MNEMONIC_SLIP39_BASIC_20_3of6, get_test_address


@pytest.mark.setup_client(mnemonic=MNEMONIC_SLIP39_BASIC_20_3of6, passphrase=True)
@pytest.mark.skip_t1
def test_3of6_passphrase(client):
    """
    BIP32 Root Key for passphrase TREZOR:
    provided by Andrew, address calculated via https://iancoleman.io/bip39/
    xprv9s21ZrQH143K2pMWi8jrTawHaj16uKk4CSbvo4Zt61tcrmuUDMx2o1Byzcr3saXNGNvHP8zZgXVdJHsXVdzYFPavxvCyaGyGr1WkAYG83ce
    """
    assert client.features.passphrase_protection is True
    client.use_passphrase("TREZOR")
    address = get_test_address(client)
    assert address == "mi4HXfRJAqCDyEdet5veunBvXLTKSxpuim"


@pytest.mark.setup_client(
    mnemonic=(
        "hobo romp academic axis august founder knife legal recover alien expect emphasis loan kitchen involve teacher capture rebuild trial numb spider forward ladle lying voter typical security quantity hawk legs idle leaves gasoline",
        "hobo romp academic agency ancestor industry argue sister scene midst graduate profile numb paid headset airport daisy flame express scene usual welcome quick silent downtown oral critical step remove says rhythm venture aunt",
    ),
    passphrase=True,
)
@pytest.mark.skip_t1
def test_2of5_passphrase(client):
    """
    BIP32 Root Key for passphrase TREZOR:
    provided by Andrew, address calculated via https://iancoleman.io/bip39/
    xprv9s21ZrQH143K2o6EXEHpVy8TCYoMmkBnDCCESLdR2ieKwmcNG48ck2XJQY4waS7RUQcXqR9N7HnQbUVEDMWYyREdF1idQqxFHuCfK7fqFni
    """
    assert client.features.passphrase_protection is True
    client.use_passphrase("TREZOR")
    address = get_test_address(client)
    assert address == "mjXH4pN7TtbHp3tWLqVKktKuaQeByHMoBZ"
