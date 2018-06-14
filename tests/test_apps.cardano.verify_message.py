from common import *
from ubinascii import unhexlify

from apps.cardano.verify_message import _verify_message


class TestCardanoVerifyMessage(unittest.TestCase):
    def test_verify_message(self):
        messages = [
            ('Test message to sign', '2df46e04ebf0816e242bfaa1c73e5ebe8863d05d7a96c8aac16f059975e63f30', '07f226da2a59c3083e80f01ef7e0ec46fc726ebe6bd15d5e9040031c342d8651bee9aee875019c41a7719674fd417ad43990988ffd371527604b6964df75960d'),
            ('New Test message to sign', '7d1de3f22f53904d007ff833fadd7cd6482ea1e83918b985b4ea33e63c16d183', '8fd3b9d8a4c30326b720de76f8de2bbf57b29b7593576eac4a3017ea23046812017136520dc2f24e9fb4da56bd87c77ea49265686653b36859b5e1e56ba9eb0f'),
            ('Another Test message to sign', 'f59a28d704df090d8fc641248bdb27d0d001da13ddb332a79cfba8a9fa7233e7', '89d63bd32c2eb92aa418b9ce0383a7cf489bc56284876c19246b70be72070d83d361fcb136e8e257b7e66029ef4a566405cda0143d251f851debd62c3c38c302'),
            ('Just another Test message to sign', '723fdc0eb1300fe7f2b9b6989216a831835a88695ba2c2d5c50c8470b7d1b239', '49d948090d30e35a88a26d8fb07aca5d68936feba2d5bd49e0d0f7c027a0c8c2955b93a7c930a3b36d23c2502c18bf39cf9b17bbba1a0965090acfb4d10a9305'),
        ]

        for (message, public_key, signature) in messages:
            result = _verify_message(unhexlify(public_key), unhexlify(signature), message)
            self.assertEqual(result, True)


if __name__ == '__main__':
    unittest.main()
