# flake8: noqa: F403,F405
from common import *  # isort:skip

from ubinascii import hexlify

from trezorminiscript import compile


class TestMiniscriptScript(unittest.TestCase):

    vectors = [
        (
            "wsh(or_d(pk(02f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9),and_v(v:pk(03a34b99f22c790c4e36b2b3c2c35a36db06226e41c692fc82b8b56ac1c540c5bd),older(144))))",
            "2102f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9ac73642103a34b99f22c790c4e36b2b3c2c35a36db06226e41c692fc82b8b56ac1c540c5bdad029000b268",
        ),
    ]

    def test_vectors(self):
        for i, o in self.vectors:
            self.assertEqual(hexlify(compile(i)), o.encode())


if __name__ == "__main__":
    unittest.main()
