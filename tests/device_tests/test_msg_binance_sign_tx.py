import pytest

from trezorlib import binance
from trezorlib.tools import parse_path

from .conftest import setup_client

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
            "signature": "97b4c2e41b0d0f61ddcf4020fff0ecb227d6df69b3dd7e657b34be0e32b956e22d0c6be5832d25353ae24af0bb223d4a5337320518c4e7708b84c8e05eb6356b",
        },
    ),
]


@pytest.mark.binance
@pytest.mark.skip_t1  # T1 support is not planned
@setup_client(
    mnemonic="offer caution gift cross surge pretty orange during eye soldier popular holiday mention east eight office fashion ill parrot vault rent devote earth cousin"
)
@pytest.mark.parametrize("message, expected_response", BINANCE_TEST_VECTORS)
def test_binance_sign_message(client, message, expected_response):
    response = binance.sign_tx(client, parse_path("m/44'/714'/0'/0/0"), message)

    assert response.public_key.hex() == expected_response["public_key"]

    assert response.signature.hex() == expected_response["signature"]
