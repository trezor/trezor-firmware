import unittest
import common
import binascii
import hashlib
import struct

from trezorlib.client import CallException
import trezorlib.types_pb2 as proto_types

def check_path(identity):
    m = hashlib.sha256()
    m.update(struct.pack("<I", identity.index))
    uri = ''
    if identity.proto: uri += identity.proto + '://'
    if identity.user: uri += identity.user + '@'
    if identity.host: uri += identity.host
    if identity.port: uri += ':' + identity.port
    if identity.path: uri += identity.path
    m.update(uri)
    print('hash:', m.hexdigest())
    (a, b, c, d, _, _, _, _) = struct.unpack('<8I', m.digest())
    address_n = [0x80000000 | 13, 0x80000000 | a, 0x80000000 | b, 0x80000000 | c, 0x80000000 | d]
    print('path:', 'm/' + '/'.join([str(x) for x in address_n]))

class TestMsgSignidentity(common.TrezorTest):

    def test_sign(self):
        self.setup_mnemonic_nopin_nopassphrase()

        hidden = binascii.unhexlify('cd8552569d6e4509266ef137584d1e62c7579b5b8ed69bbafa4b864c6521e7c2')
        visual = '2015-03-23 17:39:22'

        # URI  : https://satoshi@bitcoin.org/login
        # hash : d0e2389d4c8394a9f3e32de01104bf6e8db2d9e2bb0905d60fffa5a18fd696db
        # path : m/2147483661/2637750992/2845082444/3761103859/4005495825
        identity = proto_types.IdentityType(proto='https', user='satoshi', host='bitcoin.org', port='', path='/login', index=0)
        sig = self.client.sign_identity(identity, hidden, visual)
        self.assertEqual(sig.address, '17F17smBTX9VTZA9Mj8LM5QGYNZnmziCjL')
        self.assertEqual(binascii.hexlify(sig.public_key), '023a472219ad3327b07c18273717bb3a40b39b743756bf287fbd5fa9d263237f45')
        self.assertEqual(binascii.hexlify(sig.signature), '20f2d1a42d08c3a362be49275c3ffeeaa415fc040971985548b9f910812237bb41770bf2c8d488428799fbb7e52c11f1a3404011375e4080e077e0e42ab7a5ba02')

        # URI  : ftp://satoshi@bitcoin.org:2323/pub
        # hash : 79a6b53831c6ff224fb283587adc4ebae8fb0d734734a46c876838f52dff53f3
        # path : m/2147483661/3098912377/2734671409/3632509519/3125730426
        identity = proto_types.IdentityType(proto='ftp', user='satoshi', host='bitcoin.org', port='2323', path='/pub', index=3)
        sig = self.client.sign_identity(identity, hidden, visual)
        self.assertEqual(sig.address, '1KAr6r5qF2kADL8bAaRQBjGKYEGxn9WrbS')
        self.assertEqual(binascii.hexlify(sig.public_key), '0266cf12d2ba381c5fd797da0d64f59c07a6f1b034ad276cca6bf2729e92b20d9c')
        self.assertEqual(binascii.hexlify(sig.signature), '20bbd12dc657d534fc0f7e40186e22c447e0866a016f654f380adffa9a84e9faf412a1bb0ae908296537838cf91145e77da08681c63d07b7dca40728b9e6cb17cf')

        # URI  : ssh://satoshi@bitcoin.org
        # hash : 5fa612f558a1a3b1fb7f010b2ea0a25cb02520a0ffa202ce74a92fc6145da5f3
        # path : m/2147483661/4111640159/2980290904/2332131323/3701645358
        identity = proto_types.IdentityType(proto='ssh', user='satoshi', host='bitcoin.org', port='', path='', index=47)
        sig = self.client.sign_identity(identity, hidden, visual)
        self.assertEqual(sig.address, '')
        self.assertEqual(binascii.hexlify(sig.public_key), '03cebfae5359d6c48b8dcf9da22b2113096548407ce21da8ab28a886f750f217f4')
        self.assertEqual(binascii.hexlify(sig.signature), '00122463a8430b74b5d8c41d7c9bacc65f0eb51ceda71b9fec112e76bf2e56d8a64a66b8e019678315dc08e3be96905ea7718ec3b731e8e57e1613671ee91d1706')

if __name__ == '__main__':
    unittest.main()
