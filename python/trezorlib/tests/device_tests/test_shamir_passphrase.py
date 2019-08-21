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

from trezorlib import btc, device
from trezorlib.messages.PassphraseSourceType import HOST as PASSPHRASE_ON_HOST

from .conftest import setup_client


@setup_client(
    mnemonic=(
        "extra extend academic bishop cricket bundle tofu goat apart victim enlarge program behavior permit course armed jerky faint language modern",
        "extra extend academic acne away best indicate impact square oasis prospect painting voting guest either argue username racism enemy eclipse",
        "extra extend academic arcade born dive legal hush gross briefing talent drug much home firefly toxic analysis idea umbrella slice",
    ),
    passphrase=True,
)
@pytest.mark.skip_t1
def test_3of6_passphrase(client):
    """
    BIP32 Root Key for passphrase TREZOR:
    provided by Andrew, address calculated using T1
    xprv9s21ZrQH143K2pMWi8jrTawHaj16uKk4CSbvo4Zt61tcrmuUDMx2o1Byzcr3saXNGNvHP8zZgXVdJHsXVdzYFPavxvCyaGyGr1WkAYG83ce
    """
    assert client.debug.read_passphrase_protection() is True
    device.apply_settings(client, passphrase_source=PASSPHRASE_ON_HOST)

    client.set_passphrase("TREZOR")
    address = btc.get_address(client, "Bitcoin", [])
    assert address == "18oZEMRWurCZW1FeK8sWYyXuWx2bFqEKyX"


@setup_client(
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
    provided by Andrew, address calculated using T1
    xprv9s21ZrQH143K2o6EXEHpVy8TCYoMmkBnDCCESLdR2ieKwmcNG48ck2XJQY4waS7RUQcXqR9N7HnQbUVEDMWYyREdF1idQqxFHuCfK7fqFni
    """
    assert client.debug.read_passphrase_protection() is True
    device.apply_settings(client, passphrase_source=PASSPHRASE_ON_HOST)

    client.set_passphrase("TREZOR")
    address = btc.get_address(client, "Bitcoin", [])
    assert address == "19Fjs9AvT13Y2Nx8GtoVfADmFWnccsPinQ"
