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
        (
            "wsh(andor(pk(034cf034640859162ba19ee5a5a33e713a86e2e285b79cdaf9d5db4a07aa59f765),after(1767225600),multi(2,02f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9,03a34b99f22c790c4e36b2b3c2c35a36db06226e41c692fc82b8b56ac1c540c5bd,03defdea4cdb677750a420fee807eacf21eb9898ae79b9768766e4faa04a2d4a34)))",
            "21034cf034640859162ba19ee5a5a33e713a86e2e285b79cdaf9d5db4a07aa59f765ac64522102f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f92103a34b99f22c790c4e36b2b3c2c35a36db06226e41c692fc82b8b56ac1c540c5bd2103defdea4cdb677750a420fee807eacf21eb9898ae79b9768766e4faa04a2d4a3453ae670400b95569b168",
        )
    ]

    def test_vectors(self):
        # for i, o in self.vectors:
        #    self.assertEqual(hexlify(compile(i)), b"")
        ms = "wsh(or_d(pk({0}/0/*),and_v(v:pkh({1}/0/*),older(1))))".format(
            "tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg",
            "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
        )
        self.assertEqual(hexlify(compile(ms, 1)), "2103dcf3bc936ecb2ec57b8f468050abce8c8756e75fd74273c9977744b1a0be7d03ac736476a914ad8d0c425f6f8edaf5270528208d46e3f064906c88ad51b268".encode())


if __name__ == "__main__":
    unittest.main()
