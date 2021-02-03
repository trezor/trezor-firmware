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

from trezorlib import messages
from trezorlib.cli import btc

VECTORS_DESCRIPTORS = (  # coin, account, script_type, descriptors
    (
        "Bitcoin",
        0,
        messages.InputScriptType.SPENDADDRESS,
        (
            "pkh([5c9e228d/44'/0'/0']xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy/0/*)#vzuemqzv",
            "pkh([5c9e228d/44'/0'/0']xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy/1/*)#akecx4j5",
        ),
    ),
    (
        "Bitcoin",
        1,
        messages.InputScriptType.SPENDADDRESS,
        (
            "pkh([5c9e228d/44'/0'/1']xpub6BiVtCpG9fQQ1EW99bMSYwySbPWvzTFRQZCFgTmV3samLSZAYU7C3f4Je9vkNh7h1GAWi5Fn93BwoGBy9EAXbWTTgTnVKAbthHpxM1fXVRL/0/*)#857lnusc",
            "pkh([5c9e228d/44'/0'/1']xpub6BiVtCpG9fQQ1EW99bMSYwySbPWvzTFRQZCFgTmV3samLSZAYU7C3f4Je9vkNh7h1GAWi5Fn93BwoGBy9EAXbWTTgTnVKAbthHpxM1fXVRL/1/*)#kqm7wfqq",
        ),
    ),
    (
        "Testnet",
        0,
        messages.InputScriptType.SPENDADDRESS,
        (
            "pkh([5c9e228d/44'/1'/0']tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkkfHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U/0/*)#k65gljcw",
            "pkh([5c9e228d/44'/1'/0']tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkkfHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U/1/*)#8w3fz8gk",
        ),
    ),
    (
        "Testnet",
        1,
        messages.InputScriptType.SPENDADDRESS,
        (
            "pkh([5c9e228d/44'/1'/1']tpubDDKn3FtHc74CcBfxJ3zdSNnRacuggmGwv3KEZLJP2LAuqc3HhsQR5ZAVudcQzezzXs7T6QrDtoJJYvgyDUJ9vgWx3Y7Et4Ats1Q25U1LXvU/0/*)#nxl4wmw3",
            "pkh([5c9e228d/44'/1'/1']tpubDDKn3FtHc74CcBfxJ3zdSNnRacuggmGwv3KEZLJP2LAuqc3HhsQR5ZAVudcQzezzXs7T6QrDtoJJYvgyDUJ9vgWx3Y7Et4Ats1Q25U1LXvU/1/*)#zj65nw7f",
        ),
    ),
    (
        "Bitcoin",
        0,
        messages.InputScriptType.SPENDP2SHWITNESS,
        (
            "sh(wpkh([5c9e228d/49'/0'/0']xpub6CVKsQYXc9awxgV1tWbG4foDvdcnieK2JkbpPEBKB5WwAPKBZ1mstLbKVB4ov7QzxzjaxNK6EfmNY5Jsk2cG26EVcEkycGW4tchT2dyUhrx/0/*))#jkfqtdfw",
            "sh(wpkh([5c9e228d/49'/0'/0']xpub6CVKsQYXc9awxgV1tWbG4foDvdcnieK2JkbpPEBKB5WwAPKBZ1mstLbKVB4ov7QzxzjaxNK6EfmNY5Jsk2cG26EVcEkycGW4tchT2dyUhrx/1/*))#8h8knju3",
        ),
    ),
    (
        "Bitcoin",
        1,
        messages.InputScriptType.SPENDP2SHWITNESS,
        (
            "sh(wpkh([5c9e228d/49'/0'/1']xpub6CVKsQYXc9ax22ig3KAZMRiJL1xT9Me1sFX3t34mnVVzr6FkciU74qk7AqBkePQ2sM9pKeWp88KfPT2qcVQ19ykqGHMDioJhwywGuJ96Xt8/0/*))#xqu3tfqy",
            "sh(wpkh([5c9e228d/49'/0'/1']xpub6CVKsQYXc9ax22ig3KAZMRiJL1xT9Me1sFX3t34mnVVzr6FkciU74qk7AqBkePQ2sM9pKeWp88KfPT2qcVQ19ykqGHMDioJhwywGuJ96Xt8/1/*))#npj8nk4m",
        ),
    ),
    (
        "Testnet",
        0,
        messages.InputScriptType.SPENDP2SHWITNESS,
        (
            "sh(wpkh([5c9e228d/49'/1'/0']tpubDCHRnuvE95JrpEVTUmr36sK3K9ADf3s3aztpXzL8coBeCTE8cHV8PjxS6SjWJM3GfPn798gyEa3dRPgjoUDSuNfuC9xz4PHznwKEk2XL7X1/0/*))#qfh8hjq8",
            "sh(wpkh([5c9e228d/49'/1'/0']tpubDCHRnuvE95JrpEVTUmr36sK3K9ADf3s3aztpXzL8coBeCTE8cHV8PjxS6SjWJM3GfPn798gyEa3dRPgjoUDSuNfuC9xz4PHznwKEk2XL7X1/1/*))#4ge30d4c",
        ),
    ),
    (
        "Testnet",
        1,
        messages.InputScriptType.SPENDP2SHWITNESS,
        (
            "sh(wpkh([5c9e228d/49'/1'/1']tpubDCHRnuvE95Jrs9NkLaZwKNdoHBSoCRge6wKunXyxnspvLpx3aZbJcScTnTdsEqT6uFfWdMvBmLs3jhnkBiE7ob3xVQPV8ngDPYAMs93X9xv/0/*))#m34f6mjs",
            "sh(wpkh([5c9e228d/49'/1'/1']tpubDCHRnuvE95Jrs9NkLaZwKNdoHBSoCRge6wKunXyxnspvLpx3aZbJcScTnTdsEqT6uFfWdMvBmLs3jhnkBiE7ob3xVQPV8ngDPYAMs93X9xv/1/*))#wsmlzy80",
        ),
    ),
    (
        "Bitcoin",
        0,
        messages.InputScriptType.SPENDWITNESS,
        (
            "wpkh([5c9e228d/84'/0'/0']xpub6DDUPHpUo4pcy43iJeZjbSVWGav1SMMmuWdMHiGtkK8rhKmfbomtkwW6GKs1GGAKehT6QRocrmda3WWxXawpjmwaUHfFRXuKrXSapdckEYF/0/*)#l4dc6ccr",
            "wpkh([5c9e228d/84'/0'/0']xpub6DDUPHpUo4pcy43iJeZjbSVWGav1SMMmuWdMHiGtkK8rhKmfbomtkwW6GKs1GGAKehT6QRocrmda3WWxXawpjmwaUHfFRXuKrXSapdckEYF/1/*)#wpge8dgm",
        ),
    ),
    (
        "Bitcoin",
        1,
        messages.InputScriptType.SPENDWITNESS,
        (
            "wpkh([5c9e228d/84'/0'/1']xpub6DDUPHpUo4pd1hyVtRaknvZvCgdPdEDMKx3bB5UFcx73pEHRDVK4rwEZUgeUbVuYWGMNLvuBHp5WeyPevN2Gv7m9FnLHQE6XaKNRPZcYcHH/0/*)#y3ld2s0l",
            "wpkh([5c9e228d/84'/0'/1']xpub6DDUPHpUo4pd1hyVtRaknvZvCgdPdEDMKx3bB5UFcx73pEHRDVK4rwEZUgeUbVuYWGMNLvuBHp5WeyPevN2Gv7m9FnLHQE6XaKNRPZcYcHH/1/*)#496vh9l8",
        ),
    ),
    (
        "Testnet",
        0,
        messages.InputScriptType.SPENDWITNESS,
        (
            "wpkh([5c9e228d/84'/1'/0']tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg/0/*)#rn0zejch",
            "wpkh([5c9e228d/84'/1'/0']tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg/1/*)#j82ry8g0",
        ),
    ),
    (
        "Testnet",
        1,
        messages.InputScriptType.SPENDWITNESS,
        (
            "wpkh([5c9e228d/84'/1'/1']tpubDCZB6sR48s4T6xoXqaYxScvf23kmQvg5QpyFkYnDBjsmviKHLSG9s6cp593Exg87tuMjXXMWDvBRXnJtzppcQf8Z8HdJP1rothfxm4qnPXo/0/*)#3hdnary0",
            "wpkh([5c9e228d/84'/1'/1']tpubDCZB6sR48s4T6xoXqaYxScvf23kmQvg5QpyFkYnDBjsmviKHLSG9s6cp593Exg87tuMjXXMWDvBRXnJtzppcQf8Z8HdJP1rothfxm4qnPXo/1/*)#qrgjqk5h",
        ),
    ),
)


@pytest.mark.parametrize("coin, account, script_type, descriptors", VECTORS_DESCRIPTORS)
def test_descriptors(client, coin, account, script_type, descriptors):
    res = btc._get_descriptor(client, coin, account, script_type, show_display=True)
    assert res == descriptors
