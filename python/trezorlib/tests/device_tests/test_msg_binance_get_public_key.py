import pytest

from trezorlib import binance
from trezorlib.tools import parse_path

from .conftest import setup_client

BINANCE_PATH = parse_path("m/44h/714h/0h/0/0")


@pytest.mark.binance
@pytest.mark.skip_t1  # T1 support is not planned
@setup_client(
    mnemonic="offer caution gift cross surge pretty orange during eye soldier popular holiday mention east eight office fashion ill parrot vault rent devote earth cousin"
)
def test_binance_get_public_key(client):
    sig = binance.get_public_key(client, BINANCE_PATH)
    assert (
        sig.hex()
        == "029729a52e4e3c2b4a4e52aa74033eedaf8ba1df5ab6d1f518fd69e67bbd309b0e"
    )
