# flake8: noqa: F403,F405
from ubinascii import unhexlify

from trezor.crypto import base58
from trezor.wire import DataError

from common import unittest, utils

if not utils.BITCOIN_ONLY:
    from trezor.messages import SolanaOffchainMessageV1

    from apps.solana.constants import *
    from apps.solana.offchain_message import *
else:
    ADDRESS_SIZE = 0

MSG = "Hello, world!"

PUB0 = b"p" * ADDRESS_SIZE
PUB1 = b"q" * ADDRESS_SIZE

# Generated using Solana Kit
# https://www.solanakit.com/docs/advanced-guides/offchain-messages
TEST_VECTORS = [
    {
        "signers": ["11111111111111111111111111111111"],
        "message": "Hello, world!",
        "hex": "ff736f6c616e61206f6666636861696e0101000000000000000000000000000000000000000000000000000000000000000048656c6c6f2c20776f726c6421",
    },
    {
        "signers": ["11111111111111111111111111111111"],
        "message": "Solana off-chain message with émojis ☀️🏖️ and spëcial châräctérs! 日本語テスト ",
        "hex": "ff736f6c616e61206f6666636861696e01010000000000000000000000000000000000000000000000000000000000000000536f6c616e61206f66662d636861696e206d657373616765207769746820c3a96d6f6a697320e29880efb88ff09f8f96efb88f20616e64207370c3ab6369616c206368c3a272c3a46374c3a972732120e697a5e69cace8aa9ee38386e382b9e3838820",
    },
    {
        "signers": [
            "11111111111111111111111111111111",
            "Vote111111111111111111111111111111111111111",
            "Stake11111111111111111111111111111111111111",
        ],
        "message": "Multi-party agreement.",
        "hex": "ff736f6c616e61206f6666636861696e0103000000000000000000000000000000000000000000000000000000000000000006a1d8179137542a983437bdfe2a7ab2557f535c8a78722b68a49dc0000000000761481d357474bb7c4d7624ebd3bdb3d8355e73d11043fc0da35380000000004d756c74692d70617274792061677265656d656e742e",
    },
]


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMessageV1(unittest.TestCase):

    def serialize(self, signers=None, message=MSG):
        msg = SolanaOffchainMessageV1(
            message=message,
            signers=signers if signers is not None else [PUB0],
        )
        return serialize_offchain_message(msg)

    def test_vectors(self):
        for vector in TEST_VECTORS:
            signers = [base58.decode(signer) for signer in vector["signers"]]
            serialized = self.serialize(signers, vector["message"])
            self.assertEqual(serialized, unhexlify(vector["hex"]))

    def test_signers_empty(self):
        with self.assertRaises(DataError):
            self.serialize(signers=[])

    def test_signers_too_many(self):
        with self.assertRaises(DataError):
            self.serialize(signers=[PUB0] * 256)

    def test_signer_length_invalid(self):
        with self.assertRaises(DataError):
            self.serialize(signers=[PUB0[:-1]])
        with self.assertRaises(DataError):
            self.serialize(signers=[PUB0, PUB0[:-1]])
        with self.assertRaises(DataError):
            self.serialize(signers=[PUB0 + b"\x00"])

    def test_signers_duplicated(self):
        with self.assertRaises(DataError):
            self.serialize(signers=[PUB0, PUB0])

    def test_signers_sorted(self):
        self.assertEqual(
            self.serialize(signers=[PUB0, PUB1]),
            self.serialize(signers=[PUB1, PUB0]),
        )

    def test_message_empty(self):
        with self.assertRaises(DataError):
            self.serialize(message="")


if __name__ == "__main__":
    unittest.main()
