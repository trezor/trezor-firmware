from common import *
from ubinascii import unhexlify
from apps.common.paths import HARDENED
from apps.ethereum.sign_typed_data import encode_solidity_static, bytes_from_hex

# https://github.com/ethereum/EIPs/blob/master/EIPS/eip-712.md
class TestEthereumSignTypedData(unittest.TestCase):

    def test_encode_solidity_static(self):
        # Boolean encoding
        encoded = encode_solidity_static('bool', 'true')
        self.assertEqual(encoded, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01')

        encoded = encode_solidity_static('bool', 'false')
        self.assertEqual(encoded, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

        # Unknown value will be encoded as false
        encoded = encode_solidity_static('bool', 'unknown')
        self.assertEqual(encoded, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

        # bytesX encoding
        encoded = encode_solidity_static('bytes6', '0xbaddad')
        self.assertEqual(encoded, b'\xba\xdd\xad\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

        encoded = encode_solidity_static('bytes6', unhexlify('baddad'))
        self.assertEqual(encoded, b'\xba\xdd\xad\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

        encoded = encode_solidity_static('bytes32', '0000000000000000000000000000000000000000000000000000000000000dad')
        self.assertEqual(encoded, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0d\xad')

        encoded = encode_solidity_static('bytes32', unhexlify('0000000000000000000000000000000000000000000000000000000000000dad'))
        self.assertEqual(encoded, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0d\xad')

        # for bytesX values > 32 bytes are cutoff at the end
        encoded = encode_solidity_static('bytes33', '0X0000000000000000000000000000000000000000000000000000000000000baddad0')
        self.assertEqual(encoded, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b\xad')
        
        encoded = encode_solidity_static('bytes33', unhexlify('0000000000000000000000000000000000000000000000000000000000000baddad0'))
        self.assertEqual(encoded, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b\xad')

        # int values
        encoded = encode_solidity_static('int', '32')
        self.assertEqual(encoded, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x20')

        encoded = encode_solidity_static('uint', '0x2123')
        self.assertEqual(encoded, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x21\x23')

        # values > 32 bytes are cutoff at the beginning
        encoded = encode_solidity_static('uint', '0X0000000000000000000000000000000000000000000000000000000000000000baddad')
        self.assertEqual(encoded, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xba\xdd\xad')


    def test_bytes_from_hex(self):
        encoded = bytes_from_hex('0X00baddad')
        self.assertEqual(encoded, b'\x00\xba\xdd\xad')

        encoded = bytes_from_hex('0x00bad000')
        self.assertEqual(encoded, b'\x00\xba\xd0\x00')

        encoded = bytes_from_hex('000dad0000')
        self.assertEqual(encoded, b'\x00\x0d\xad\x00\x00')

        encoded = bytes_from_hex('')
        self.assertEqual(encoded, bytes())

        encoded = bytes_from_hex('0x')
        self.assertEqual(encoded, b'')

        encoded = bytes_from_hex('0X')
        self.assertEqual(encoded, b'')


if __name__ == '__main__':
    unittest.main()
