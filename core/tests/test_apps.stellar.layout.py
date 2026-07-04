# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.messages import (
        StellarInt128Parts,
        StellarInt256Parts,
        StellarUInt128Parts,
        StellarUInt256Parts,
    )

    from apps.stellar.operations.layout import (
        _format_i128,
        _format_i256,
        _format_u128,
        _format_u256,
    )


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestStellarFormatIntegers(unittest.TestCase):
    def test_format_u128(self):
        TESTS = [
            (StellarUInt128Parts(hi=0, lo=0), "0"),
            (StellarUInt128Parts(hi=0, lo=1), "1"),
            (StellarUInt128Parts(hi=1, lo=0), str(2**64)),
            (
                StellarUInt128Parts(hi=0xFFFFFFFFFFFFFFFF, lo=0xFFFFFFFFFFFFFFFF),
                str(2**128 - 1),
            ),
        ]
        for parts, expected in TESTS:
            self.assertEqual(_format_u128(parts), expected)

    def test_format_i128(self):
        TESTS = [
            (StellarInt128Parts(hi=0, lo=0), "0"),
            (StellarInt128Parts(hi=0, lo=1), "1"),
            (StellarInt128Parts(hi=-1, lo=0xFFFFFFFFFFFFFFFF), "-1"),
            (StellarInt128Parts(hi=1, lo=0), str(2**64)),
            (StellarInt128Parts(hi=-1, lo=0), str(-(2**64))),
            (
                StellarInt128Parts(hi=0x7FFFFFFFFFFFFFFF, lo=0xFFFFFFFFFFFFFFFF),
                str(2**127 - 1),
            ),
            (StellarInt128Parts(hi=-0x8000000000000000, lo=0), str(-(2**127))),
        ]
        for parts, expected in TESTS:
            self.assertEqual(_format_i128(parts), expected)

    def test_format_u256(self):
        TESTS = [
            (StellarUInt256Parts(hi_hi=0, hi_lo=0, lo_hi=0, lo_lo=0), "0"),
            (StellarUInt256Parts(hi_hi=0, hi_lo=0, lo_hi=0, lo_lo=1), "1"),
            (StellarUInt256Parts(hi_hi=0, hi_lo=0, lo_hi=1, lo_lo=0), str(2**64)),
            (StellarUInt256Parts(hi_hi=0, hi_lo=1, lo_hi=0, lo_lo=0), str(2**128)),
            (StellarUInt256Parts(hi_hi=1, hi_lo=0, lo_hi=0, lo_lo=0), str(2**192)),
            (
                StellarUInt256Parts(
                    hi_hi=0xFFFFFFFFFFFFFFFF,
                    hi_lo=0xFFFFFFFFFFFFFFFF,
                    lo_hi=0xFFFFFFFFFFFFFFFF,
                    lo_lo=0xFFFFFFFFFFFFFFFF,
                ),
                str(2**256 - 1),
            ),
        ]
        for parts, expected in TESTS:
            self.assertEqual(_format_u256(parts), expected)

    def test_format_i256(self):
        TESTS = [
            (StellarInt256Parts(hi_hi=0, hi_lo=0, lo_hi=0, lo_lo=0), "0"),
            (StellarInt256Parts(hi_hi=0, hi_lo=0, lo_hi=0, lo_lo=1), "1"),
            (
                StellarInt256Parts(
                    hi_hi=-1,
                    hi_lo=0xFFFFFFFFFFFFFFFF,
                    lo_hi=0xFFFFFFFFFFFFFFFF,
                    lo_lo=0xFFFFFFFFFFFFFFFF,
                ),
                "-1",
            ),
            (StellarInt256Parts(hi_hi=0, hi_lo=0, lo_hi=1, lo_lo=0), str(2**64)),
            (
                StellarInt256Parts(
                    hi_hi=-1, hi_lo=0xFFFFFFFFFFFFFFFF, lo_hi=0xFFFFFFFFFFFFFFFF, lo_lo=0
                ),
                str(-(2**64)),
            ),
            (StellarInt256Parts(hi_hi=0, hi_lo=1, lo_hi=0, lo_lo=0), str(2**128)),
            (
                StellarInt256Parts(hi_hi=-1, hi_lo=0xFFFFFFFFFFFFFFFF, lo_hi=0, lo_lo=0),
                str(-(2**128)),
            ),
            (StellarInt256Parts(hi_hi=1, hi_lo=0, lo_hi=0, lo_lo=0), str(2**192)),
            (StellarInt256Parts(hi_hi=-1, hi_lo=0, lo_hi=0, lo_lo=0), str(-(2**192))),
            (
                StellarInt256Parts(
                    hi_hi=0x7FFFFFFFFFFFFFFF,
                    hi_lo=0xFFFFFFFFFFFFFFFF,
                    lo_hi=0xFFFFFFFFFFFFFFFF,
                    lo_lo=0xFFFFFFFFFFFFFFFF,
                ),
                str(2**255 - 1),
            ),
            (
                StellarInt256Parts(hi_hi=-0x8000000000000000, hi_lo=0, lo_hi=0, lo_lo=0),
                str(-(2**255)),
            ),
        ]
        for parts, expected in TESTS:
            self.assertEqual(_format_i256(parts), expected)


if __name__ == "__main__":
    unittest.main()
