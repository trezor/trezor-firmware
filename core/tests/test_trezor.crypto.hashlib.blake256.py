from common import *

from trezor.crypto import hashlib


class TestCryptoBlake256(unittest.TestCase):

    # vectors from https://raw.githubusercontent.com/monero-project/monero/master/tests/hash/tests-extra-blake.txt

    vectors = [
        ('', '716f6e863f744b9ac22c97ec7b76ea5f5908bc5b2f67c61510bfc4751384ea7a'),
        ('cc', 'e104256a2bc501f459d03fac96b9014f593e22d30f4de525fa680c3aa189eb4f'),
        ('41fb', '8f341148be7e354fdf38b693d8c6b4e0bd57301a734f6fd35cd85b8491c3ddcd'),
        ('1f877c', 'bc334d1069099f10c601883ac6f3e7e9787c6aa53171f76a21923cc5ad3ab937'),
        ('c1ecfdfc', 'b672a16f53982bab1e77685b71c0a5f6703ffd46a1c834be69f614bd128d658e'),
        ('21f134ac57', 'd9134b2899057a7d8d320cc99e3e116982bc99d3c69d260a7f1ed3da8be68d99'),
        ('c6f50bb74e29', '637923bd29a35aa3ecbbd2a50549fc32c14cf0fdcaf41c3194dd7414fd224815'),
        ('119713cc83eeef', '70c092fd5c8c21e9ef4bbc82a5c7819e262a530a748caf285ff0cba891954f1e'),
        ('4a4f202484512526', 'fdf092993edbb7a0dc7ca67f04051bbd14481639da0808947aff8bfab5abed4b'),
        ('1f66ab4185ed9b6375', '6f6fc234bf35beae1a366c44c520c59ad5aa70351b5f5085e21e1fe2bfcee709'),
        ('eed7422227613b6f53c9', '4fdaf89e2a0e78c000061b59455e0ea93a4445b440e7562c8f0cfa165c93de2e'),
        ('eaeed5cdffd89dece455f1', 'd6b780eee9c811f664393dc2c58b5a68c92b3c9fe9ceb70371d33ece63b5787e'),
        ('5be43c90f22902e4fe8ed2d3', 'd0015071d3e7ed048c764850d76406eceae52b8e2e6e5a2c3aa92ae880485b34'),
        ('a746273228122f381c3b46e4f1', '9b0207902f9932f7a85c24722e93e31f6ed2c75c406509aa0f2f6d1cab046ce4'),
        ('3c5871cd619c69a63b540eb5a625', '258020d5b04a814f2b72c1c661e1f5a5c395d9799e5eee8b8519cf7300e90cb1'),
        ('fa22874bcc068879e8ef11a69f0722', '4adae3b55baa907fefc253365fdd99d8398befd0551ed6bf9a2a2784d3c304d1'),
        ('52a608ab21ccdd8a4457a57ede782176', '6dd10d772f8d5b4a96c3c5d30878cd9a1073fa835bfe6d2b924fa64a1fab1711'),
        ('82e192e4043ddcd12ecf52969d0f807eed', '0b8741ddf2259d3af2901eb1ae354f22836442c965556f5c1eb89501191cb46a'),
        ('75683dcb556140c522543bb6e9098b21a21e', 'f48a754ca8193a82643150ab94038b5dd170b4ebd1e0751b78cfb0a98fa5076a'),
        ('06e4efe45035e61faaf4287b4d8d1f12ca97e5', '5698409ab856b74d9fa5e9b259dfa46001f89041752da424e56e491577b88c86'),
    ]

    def test_digest(self):
        for b, d in self.vectors:
            self.assertEqual(hashlib.blake256(unhexlify(b)).digest(), unhexlify(d))

    def test_update(self):

        for b, d in self.vectors:
            x = hashlib.blake256()
            x.update(unhexlify(b))
            self.assertEqual(x.digest(), unhexlify(d))

    def test_digest_multi(self):
        x = hashlib.blake256()
        d0 = x.digest()
        d1 = x.digest()
        d2 = x.digest()
        self.assertEqual(d0, d1)
        self.assertEqual(d0, d2)


if __name__ == '__main__':
    unittest.main()
