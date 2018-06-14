from common import *

from apps.cardano.sign_message import _sign_message
from trezor.crypto import bip32


class TestCardanoSignMessage(unittest.TestCase):
    def test_sign_message(self):
        mnemonic = "plastic that delay conduct police ticket swim gospel intact harsh obtain entire"
        node = bip32.from_mnemonic_cardano(mnemonic)

        messages = [
            ('Test message to sign', [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0x80000000], '07f226da2a59c3083e80f01ef7e0ec46fc726ebe6bd15d5e9040031c342d8651bee9aee875019c41a7719674fd417ad43990988ffd371527604b6964df75960d'),
            ('New Test message to sign', [0x80000000 | 44, 0x80000000 | 1815], '8fd3b9d8a4c30326b720de76f8de2bbf57b29b7593576eac4a3017ea23046812017136520dc2f24e9fb4da56bd87c77ea49265686653b36859b5e1e56ba9eb0f'),
            ('Another Test message to sign', [0x80000000 | 44, 0x80000000 | 1815, 0, 0, 0], '89d63bd32c2eb92aa418b9ce0383a7cf489bc56284876c19246b70be72070d83d361fcb136e8e257b7e66029ef4a566405cda0143d251f851debd62c3c38c302'),
            ('Just another Test message to sign', [0x80000000 | 44, 0x80000000 | 1815, 0x80000000, 0, 0], '49d948090d30e35a88a26d8fb07aca5d68936feba2d5bd49e0d0f7c027a0c8c2955b93a7c930a3b36d23c2502c18bf39cf9b17bbba1a0965090acfb4d10a9305'),
        ]

        for (message, derivation_path, expected_signature) in messages:
            signature = _sign_message(node, message, derivation_path)
            self.assertEqual(expected_signature, hexlify(signature.signature).decode('utf8'))


if __name__ == '__main__':
    unittest.main()
