import pytest

from trezorlib.eos import get_public_key
from trezorlib.tools import parse_path

from .common import TrezorTest


@pytest.mark.skip_t1
@pytest.mark.eos
class TestMsgEosGetpublickey(TrezorTest):
    def test_eos_get_public_key(self):
        self.setup_mnemonic_nopin_nopassphrase()
        public_key = get_public_key(self.client, parse_path("m/44'/194'/0'/0/0"))
        assert (
            public_key.wif_public_key
            == "PUB_K1_4u6Sfnzj4Sh2pEQnkXyZQJqH3PkKjGByDCbsqqmyq6PttM9KyB"
        )
        assert (
            public_key.raw_public_key.hex()
            == "02015fabe197c955036bab25f4e7c16558f9f672f9f625314ab1ec8f64f7b1198e"
        )
        public_key = get_public_key(self.client, parse_path("m/44'/194'/0'/0/1"))
        assert (
            public_key.wif_public_key
            == "PUB_K1_5d1VP15RKxT4dSakWu2TFuEgnmaGC2ckfSvQwND7pZC1tXkfLP"
        )
        assert (
            public_key.raw_public_key.hex()
            == "02608bc2c431521dee0b9d5f2fe34053e15fc3b20d2895e0abda857b9ed8e77a78"
        )
        public_key = get_public_key(self.client, parse_path("m/44'/194'/1'/0/0"))
        assert (
            public_key.wif_public_key
            == "PUB_K1_7UuNeTf13nfcG85rDB7AHGugZi4C4wJ4ft12QRotqNfxdV2NvP"
        )
        assert (
            public_key.raw_public_key.hex()
            == "035588a197bd5a7356e8a702361b2d535c6372f843874bed6617cd1afe1dfcb502"
        )
