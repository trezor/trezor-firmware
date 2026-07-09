# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from apps.tron.helpers import address_from_public_key


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestTronAddress(unittest.TestCase):
    def test_pubkey_to_address(self):
        addr = address_from_public_key(
            unhexlify(
                "04aee772c640a56bfd434cc6c41b661467f0fac8ad922cd0d6f37a25a9faab506c9d687d8d4ad0957ca8a07b15db6b39ab2fa56cc81b49f2f92d44e1cdd2f4f266"
            )
        )
        self.assertEqual(addr, "TY72iA3SBtrds3QLYsS7LwYfkzXwAXCRWT")

        addr = address_from_public_key(
            unhexlify(
                "041cc8ed55001c441a9ca7b42129f025f33ff30ea29dfe88fc9f8ad8826582c73b52d47c475c75da0cc9f64a6462ca57e70a8902a79cccc4e769cc0261c691ce4f"
            )
        )
        self.assertEqual(addr, "TVd6xm7E5vn9qnUQZbfoH5SAVZXZ15c4wC")

        addr = address_from_public_key(
            unhexlify(
                "04d3df47d402249892f56295cf08cb70c2e37fc6b9eea01e1b163f4b5608f96c8449b3ea69541a33ff7961bb69af6f98bfca558fe53b9429de3fb8054d29f9c917"
            )
        )
        self.assertEqual(addr, "TL4A3PZDdZxZnsk7ZsVgo5ztWaZqWLQT8i")


if __name__ == "__main__":
    unittest.main()
