# flake8: noqa: F403,F405
from common import *  # isort:skip

if utils.USE_THP:
    from trezor.wire.thp import cpace


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestTrezorHostProtocolCPace(unittest.TestCase):
    # Vectors from https://www.ietf.org/archive/id/draft-irtf-cfrg-cpace-21.html#name-test-vectors-for-g_x25519sc
    # Vectors ending in _256 have the last bit set to 1. This bit is ignored by the curve25519
    # implementation - as is specified by the RFC 7748.
    vectors_raise = {
        ("u0", "0000000000000000000000000000000000000000000000000000000000000000"),
        ("u1", "0100000000000000000000000000000000000000000000000000000000000000"),
        ("u2", "ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f"),
        ("u3", "e0eb7a7c3b41b8ae1656e3faf19fc46ada098deb9c32b1fd866205165f49b800"),
        ("u4", "5f9c95bca3508c24b1d0b1559c83ef5b04445cc4581c8e86d8224eddd09f1157"),
        ("u5", "edffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f"),
        ("u7", "eeffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f"),
        ("u0_256", "0000000000000000000000000000000000000000000000000000000000000080"),
        ("u1_256", "0100000000000000000000000000000000000000000000000000000000000080"),
        ("u2_256", "ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"),
        ("u3_256", "e0eb7a7c3b41b8ae1656e3faf19fc46ada098deb9c32b1fd866205165f49b880"),
        ("u4_256", "5f9c95bca3508c24b1d0b1559c83ef5b04445cc4581c8e86d8224eddd09f11d7"),
        ("u5_256", "edffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"),
        ("u7_256", "eeffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"),
    }
    # Vectors from https://www.ietf.org/archive/id/draft-irtf-cfrg-cpace-21.html#name-test-vectors-for-g_x25519sc
    # that degrade to low-order points when the last bit is not ignored as specified in RFC 7748.
    vectors_valid = {
        (
            "u6",
            "daffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            "d8e2c776bbacd510d09fd9278b7edcd25fc5ae9adfba3b6e040e8d3b71b21806",
        ),
        (
            "u8",
            "dbffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            "c85c655ebe8be44ba9c0ffde69f2fe10194458d137f09bbff725ce58803cdb38",
        ),
        (
            "u9",
            "d9ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            "db64dafa9b8fdd136914e61461935fe92aa372cb056314e1231bc4ec12417456",
        ),
        (
            "ua",
            "cdeb7a7c3b41b8ae1656e3faf19fc46ada098deb9c32b1fd866205165f49b880",
            "e062dcd5376d58297be2618c7498f55baa07d7e03184e8aada20bca28888bf7a",
        ),
        (
            "ub",
            "4c9c95bca3508c24b1d0b1559c83ef5b04445cc4581c8e86d8224eddd09f11d7",
            "993c6ad11c4c29da9a56f7691fd0ff8d732e49de6250b6c2e80003ff4629a175",
        ),
    }

    def test_compute_shared_secret(self):
        ctx = cpace.Cpace(b"")
        s = unhexlify(
            "af46e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449aff"
        )
        ctx.trezor_private_key = s
        for _, input in self.vectors_raise:
            self.assertRaises(ValueError, ctx.compute_shared_secret, unhexlify(input))
        for _, input, expected_out in self.vectors_valid:
            ctx.compute_shared_secret(unhexlify(input))
            self.assertEqual(hexlify(ctx.shared_secret).decode(), expected_out)


if __name__ == "__main__":
    unittest.main()
