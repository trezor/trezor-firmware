import unittest
import common
import binascii

from trezorlib.client import CallException

class TestMsgEncryptmessage(common.TrezorTest):

    def test_encrypt(self):
        self.setup_mnemonic_nopin_nopassphrase()

        pubkey1 = self.client.get_public_node([1]).public_key

        enc = self.client.encrypt_message(pubkey1, 'testing message!', display_only=False)
        self.assertEqual(binascii.hexlify(enc), '42494531025bef848e6a92f9361eeb23ba4f7d642191c9be17d6868b3e17839d8cb4b96045bbb05c7936312088ea97d473bcfbbe020c6c67028130601022ec45ec7b34c8eb47ee785922c308c9ad25da259aa59ec21a89e327af30e4213da31f3fc70ff5ae')

        enc = self.client.encrypt_message(pubkey1, 'testing message!', display_only=True)
        self.assertEqual(binascii.hexlify(enc), '42494531025bef848e6a92f9361eeb23ba4f7d642191c9be17d6868b3e17839d8cb4b96045bbb05c7936312088ea97d473bcfbbe02f14a9778cbb1c5b75f8cef70581ad2c34acb7f9eb7918b17ea323123148251d8eb6d63d16ac8a86f3623855450b70d95')

        pubkey2 = self.client.get_public_node([1, -2]).public_key

        enc = self.client.encrypt_message(pubkey2, 'testing message!', display_only=False)
        self.assertEqual(binascii.hexlify(enc), '424945310238cba33fd1ed1d2adebd4cc4bbd89913ecb34922c1b387c3a10d70d9de6d9ea627b49044ce1dbf26cca8a727a40366dcb1f9c9a2d5eafa90817fd0d967ca25127bea98a5e93c150544bf457b48fdd667c72b8c9c31ccd0ad2aea2f1b50ec0ce6')

        enc = self.client.encrypt_message(pubkey2, 'testing message!', display_only=True)
        self.assertEqual(binascii.hexlify(enc), '424945310238cba33fd1ed1d2adebd4cc4bbd89913ecb34922c1b387c3a10d70d9de6d9ea627b49044ce1dbf26cca8a727a40366dc1b16f7f6acb09645d91c73619baf458ed3262da40ff25f8f64db3fd5ff19bf50fb589db3ae6cfb5b546af720aa711d81')

if __name__ == '__main__':
    unittest.main()
