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

from trezorlib import binance
from trezorlib.tools import parse_path

BINANCE_TEST_VECTORS = [
    (  # CANCEL
        {
            "account_number": "34",
            "chain_id": "Binance-Chain-Nile",
            "data": "null",
            "memo": "",
            "msgs": [
                {
                    "refid": "BA36F0FAD74D8F41045463E4774F328F4AF779E5-29",
                    "sender": "tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd",
                    "symbol": "BCHSV.B-10F_BNB",
                }
            ],
            "sequence": "33",
            "source": "1",
        },
        {
            "public_key": "029729a52e4e3c2b4a4e52aa74033eedaf8ba1df5ab6d1f518fd69e67bbd309b0e",
            "signature": "d93fb0402b2b30e7ea08e123bb139ad68bf0a1577f38592eb22d11e127f09bbd3380f29b4bf15bdfa973454c5c8ed444f2e256e956fe98cfd21e886a946e21e5",
        },
    ),
    (  # ORDER
        {
            "account_number": "34",
            "chain_id": "Binance-Chain-Nile",
            "data": "null",
            "memo": "",
            "msgs": [
                {
                    "id": "BA36F0FAD74D8F41045463E4774F328F4AF779E5-33",
                    "ordertype": 2,
                    "price": 100000000,
                    "quantity": 100000000,
                    "sender": "tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd",
                    "side": 1,
                    "symbol": "ADA.B-B63_BNB",
                    "timeinforce": 1,
                }
            ],
            "sequence": "32",
            "source": "1",
        },
        {
            "public_key": "029729a52e4e3c2b4a4e52aa74033eedaf8ba1df5ab6d1f518fd69e67bbd309b0e",
            "signature": "851fc9542342321af63ecbba7d3ece545f2a42bad01ba32cff5535b18e54b6d3106e10b6a4525993d185a1443d9a125186960e028eabfdd8d76cf70a3a7e3100",
        },
    ),
    (  # TRANSFER
        {
            "account_number": "34",
            "chain_id": "Binance-Chain-Nile",
            "data": "null",
            "memo": "test",
            "msgs": [
                {
                    "inputs": [
                        {
                            "address": "tbnb1hgm0p7khfk85zpz5v0j8wnej3a90w709zzlffd",
                            "coins": [{"amount": 1000000000, "denom": "BNB"}],
                        }
                    ],
                    "outputs": [
                        {
                            "address": "tbnb1ss57e8sa7xnwq030k2ctr775uac9gjzglqhvpy",
                            "coins": [{"amount": 1000000000, "denom": "BNB"}],
                        }
                    ],
                }
            ],
            "sequence": "31",
            "source": "1",
        },
        {
            "public_key": "029729a52e4e3c2b4a4e52aa74033eedaf8ba1df5ab6d1f518fd69e67bbd309b0e",
            "signature": "faf5b908d6c4ec0c7e2e7d8f7e1b9ca56ac8b1a22b01655813c62ce89bf84a4c7b14f58ce51e85d64c13f47e67d6a9187b8f79f09e0a9b82019f47ae190a4db3",
        },
    ),
]


@pytest.mark.altcoin
@pytest.mark.binance
@pytest.mark.skip_t1  # T1 support is not planned
@pytest.mark.setup_client(
    mnemonic="offer caution gift cross surge pretty orange during eye soldier popular holiday mention east eight office fashion ill parrot vault rent devote earth cousin"
)
@pytest.mark.parametrize("message, expected_response", BINANCE_TEST_VECTORS)
def test_binance_sign_message(client, message, expected_response):
    response = binance.sign_tx(client, parse_path("m/44'/714'/0'/0/0"), message)

    assert response.public_key.hex() == expected_response["public_key"]

    assert response.signature.hex() == expected_response["signature"]
