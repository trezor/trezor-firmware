# flake8: noqa: F403,F405
from trezor.crypto import base58
from trezor.wire import DataError

from common import unittest, utils

if not utils.BITCOIN_ONLY:
    from apps.solana.constants import *
    from apps.solana.offchain_message import *

    DOM = OffchainMessage.SIGNING_DOMAIN
    APP = b"a" * OffchainMessageV0.APP_DOMAIN_LEN
else:
    DOM = b""
    APP = b""
    ADDRESS_SIZE = 0


VER_0 = b"\x00"

FORM_ASCII = b"\x00"
FORM_UTF8_S = b"\x01"
FORM_UTF8_L = b"\x02"

MSG_ASCII = b"Hello, world!"
MSG_UTF8_S = "Hello, 🌍!".encode()
MSG_UTF8_L = MSG_UTF8_S * 1000

PUB0 = b"p" * ADDRESS_SIZE
PUB1 = b"q" * ADDRESS_SIZE

# Generated using Solana Kit
# https://www.solanakit.com/docs/advanced-guides/offchain-messages
TEST_VECTORS = [
    {
        "app": "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
        "signers": ["11111111111111111111111111111111"],
        "message": "Hello, world!",
        "format": 0,
        "hex": "ff736f6c616e61206f6666636861696e00054a535a992921064d24e87160da387c7c35b5ddbc92bb81e41fa8404105448d000100000000000000000000000000000000000000000000000000000000000000000d0048656c6c6f2c20776f726c6421",
    },
    {
        "app": "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
        "signers": ["11111111111111111111111111111111"],
        "message": "Solana off-chain message with émojis ☀️🏖️ and spëcial châräctérs! 日本語テスト ",
        "format": 1,
        "hex": "ff736f6c616e61206f6666636861696e00054a535a992921064d24e87160da387c7c35b5ddbc92bb81e41fa8404105448d010100000000000000000000000000000000000000000000000000000000000000006300536f6c616e61206f66662d636861696e206d657373616765207769746820c3a96d6f6a697320e29880efb88ff09f8f96efb88f20616e64207370c3ab6369616c206368c3a272c3a46374c3a972732120e697a5e69cace8aa9ee38386e382b9e3838820",
    },
    {
        "app": "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
        "signers": ["11111111111111111111111111111111"],
        "message": "This uses the extended UTF-8 format allowing up to 65535 bytes.",
        "format": 2,
        "hex": "ff736f6c616e61206f6666636861696e00054a535a992921064d24e87160da387c7c35b5ddbc92bb81e41fa8404105448d020100000000000000000000000000000000000000000000000000000000000000003f005468697320757365732074686520657874656e646564205554462d3820666f726d617420616c6c6f77696e6720757020746f2036353533352062797465732e",
    },
    {
        "app": "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
        "signers": [
            "11111111111111111111111111111111",
            "Vote111111111111111111111111111111111111111",
            "Stake11111111111111111111111111111111111111",
        ],
        "message": "Multi-party agreement.",
        "format": 0,
        "hex": "ff736f6c616e61206f6666636861696e00054a535a992921064d24e87160da387c7c35b5ddbc92bb81e41fa8404105448d000300000000000000000000000000000000000000000000000000000000000000000761481d357474bb7c4d7624ebd3bdb3d8355e73d11043fc0da353800000000006a1d8179137542a983437bdfe2a7ab2557f535c8a78722b68a49dc00000000016004d756c74692d70617274792061677265656d656e742e",
    },
]


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMessageV0(unittest.TestCase):

    def assertMsgEqual(self, offchain, app, signers, form, message):
        self.assertEqual(offchain.app, app)
        self.assertListEqual(offchain.signers, signers)
        self.assertEqual(offchain.format, form)
        self.assertEqual(offchain.message, message)

    def try_parse(
        self,
        dom=DOM,
        ver=VER_0,
        app=APP,
        pubs=(PUB0,),
        n_pubs=None,
        form=FORM_ASCII,
        msg=MSG_ASCII,
        msg_len=None,
    ):
        if n_pubs is None:
            n_pubs = len(pubs).to_bytes(1, "little")
        if msg_len is None:
            msg_len = len(msg).to_bytes(2, "little")

        data = dom + ver + app + form + n_pubs + b"".join(pubs) + msg_len + msg
        offchain = OffchainMessage.from_bytes(data)

        self.assertMsgEqual(offchain, app, pubs, form[0], msg.decode())

        return data, offchain

    def test_vectors(self):
        for vector in TEST_VECTORS:
            offchain = OffchainMessage.from_bytes(bytes.fromhex(vector["hex"]))

            self.assertMsgEqual(
                offchain,
                base58.decode(vector["app"]),
                [base58.decode(s) for s in vector["signers"]],
                vector["format"],
                vector["message"],
            )

    def test_basic(self):
        configs = (
            (FORM_ASCII, MSG_ASCII),
            (FORM_UTF8_S, MSG_ASCII),
            (FORM_UTF8_S, MSG_UTF8_S),
            (FORM_UTF8_L, MSG_ASCII),
            (FORM_UTF8_L, MSG_UTF8_S),
            (FORM_UTF8_L, MSG_UTF8_L),
        )

        for form, msg in configs:
            self.try_parse(form=form, msg=msg)

    def test_multi(self):
        self.try_parse(pubs=[PUB0, PUB1])

    def test_domain_invalid(self):
        with self.assertRaises(DataError):
            self.try_parse(dom=b"\x00solana offchain")

    def test_version_unsupported(self):
        with self.assertRaises(DataError):
            self.try_parse(ver=b"\xff")

    def test_format_mismatch(self):
        with self.assertRaises(DataError):
            self.try_parse(form=FORM_ASCII, msg=MSG_UTF8_S)
        with self.assertRaises(DataError):
            self.try_parse(form=FORM_UTF8_S, msg=MSG_UTF8_L)

    def test_format_invalid(self):
        with self.assertRaises(DataError):
            self.try_parse(form=b"\x03")

    def test_ascii_restricted(self):
        self.try_parse(form=FORM_ASCII, msg=bytes(range(0x20, 0x7F)))

    def test_ascii_unrestricted(self):
        with self.assertRaises(DataError):
            self.try_parse(form=FORM_ASCII, msg=b"\x1f")
        with self.assertRaises(DataError):
            self.try_parse(form=FORM_ASCII, msg=b"\x7f")

    def test_utf8_invalid(self):
        with self.assertRaises(DataError):
            self.try_parse(form=FORM_UTF8_S, msg=b"\xff\xfe")

    def test_signer_count_zero(self):
        with self.assertRaises(DataError):
            self.try_parse(pubs=[], n_pubs=b"\x00")

    def test_signer_count_mismatch(self):
        with self.assertRaises(DataError):
            self.try_parse(pubs=[PUB0, PUB1], n_pubs=b"\x01")
        with self.assertRaises(DataError):
            self.try_parse(pubs=[PUB0], n_pubs=b"\x02")

    def test_message_length_zero(self):
        with self.assertRaises(DataError):
            self.try_parse(msg=b"", msg_len=b"\x00\x00")

    def test_message_length_mismatch(self):
        with self.assertRaises(DataError):
            self.try_parse(msg=b"12345", msg_len=b"\x06\x00")
        with self.assertRaises(DataError):
            self.try_parse(msg=b"12345", msg_len=b"\x04\x00")

    def test_message_length_limits(self):
        configs = (
            (FORM_ASCII, OffchainMessageV0.MAX_COMBINED_MSG_LEN_SHORT),
            (FORM_UTF8_S, OffchainMessageV0.MAX_COMBINED_MSG_LEN_SHORT),
            (FORM_UTF8_L, OffchainMessageV0.MAX_COMBINED_MSG_LEN),
        )
        PREAMBLE_LEN = 0x35 + ADDRESS_SIZE  # for 1 signer

        for form, max_len in configs:
            max_msg_len = max_len - PREAMBLE_LEN
            msg = b"m" * max_msg_len

            msg_bytes, _ = self.try_parse(form=form, msg=msg)
            self.assertEqual(len(msg_bytes), max_len)

            with self.assertRaises(DataError):
                self.try_parse(form=form, msg=msg + b"m")


if __name__ == "__main__":
    unittest.main()
