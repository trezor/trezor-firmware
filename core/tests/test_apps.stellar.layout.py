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
        parts = StellarUInt128Parts(hi=0, lo=0)
        self.assertEqual(_format_u128(parts), "0")

        parts = StellarUInt128Parts(hi=0, lo=1)
        self.assertEqual(_format_u128(parts), "1")

        parts = StellarUInt128Parts(hi=1, lo=0)
        self.assertEqual(_format_u128(parts), str(2**64))

        parts = StellarUInt128Parts(hi=0xFFFFFFFFFFFFFFFF, lo=0xFFFFFFFFFFFFFFFF)
        self.assertEqual(_format_u128(parts), str(2**128 - 1))

    def test_format_i128(self):
        parts = StellarInt128Parts(hi=0, lo=0)
        self.assertEqual(_format_i128(parts), "0")

        parts = StellarInt128Parts(hi=0, lo=1)
        self.assertEqual(_format_i128(parts), "1")

        parts = StellarInt128Parts(hi=-1, lo=0xFFFFFFFFFFFFFFFF)
        self.assertEqual(_format_i128(parts), "-1")

        parts = StellarInt128Parts(hi=1, lo=0)
        self.assertEqual(_format_i128(parts), str(2**64))

        parts = StellarInt128Parts(hi=-1, lo=0)
        self.assertEqual(_format_i128(parts), str(-(2**64)))

        parts = StellarInt128Parts(hi=0x7FFFFFFFFFFFFFFF, lo=0xFFFFFFFFFFFFFFFF)
        self.assertEqual(_format_i128(parts), str(2**127 - 1))

        parts = StellarInt128Parts(hi=-0x8000000000000000, lo=0)
        self.assertEqual(_format_i128(parts), str(-(2**127)))

    def test_format_u256(self):
        parts = StellarUInt256Parts(hi_hi=0, hi_lo=0, lo_hi=0, lo_lo=0)
        self.assertEqual(_format_u256(parts), "0")

        parts = StellarUInt256Parts(hi_hi=0, hi_lo=0, lo_hi=0, lo_lo=1)
        self.assertEqual(_format_u256(parts), "1")

        parts = StellarUInt256Parts(hi_hi=0, hi_lo=0, lo_hi=1, lo_lo=0)
        self.assertEqual(_format_u256(parts), str(2**64))

        parts = StellarUInt256Parts(hi_hi=0, hi_lo=1, lo_hi=0, lo_lo=0)
        self.assertEqual(_format_u256(parts), str(2**128))

        parts = StellarUInt256Parts(hi_hi=1, hi_lo=0, lo_hi=0, lo_lo=0)
        self.assertEqual(_format_u256(parts), str(2**192))

        parts = StellarUInt256Parts(
            hi_hi=0xFFFFFFFFFFFFFFFF,
            hi_lo=0xFFFFFFFFFFFFFFFF,
            lo_hi=0xFFFFFFFFFFFFFFFF,
            lo_lo=0xFFFFFFFFFFFFFFFF,
        )
        self.assertEqual(_format_u256(parts), str(2**256 - 1))

    def test_format_i256(self):
        parts = StellarInt256Parts(hi_hi=0, hi_lo=0, lo_hi=0, lo_lo=0)
        self.assertEqual(_format_i256(parts), "0")

        parts = StellarInt256Parts(hi_hi=0, hi_lo=0, lo_hi=0, lo_lo=1)
        self.assertEqual(_format_i256(parts), "1")

        parts = StellarInt256Parts(
            hi_hi=-1,
            hi_lo=0xFFFFFFFFFFFFFFFF,
            lo_hi=0xFFFFFFFFFFFFFFFF,
            lo_lo=0xFFFFFFFFFFFFFFFF,
        )
        self.assertEqual(_format_i256(parts), "-1")

        parts = StellarInt256Parts(hi_hi=0, hi_lo=0, lo_hi=1, lo_lo=0)
        self.assertEqual(_format_i256(parts), str(2**64))

        parts = StellarInt256Parts(
            hi_hi=-1, hi_lo=0xFFFFFFFFFFFFFFFF, lo_hi=0xFFFFFFFFFFFFFFFF, lo_lo=0
        )
        self.assertEqual(_format_i256(parts), str(-(2**64)))

        parts = StellarInt256Parts(hi_hi=0, hi_lo=1, lo_hi=0, lo_lo=0)
        self.assertEqual(_format_i256(parts), str(2**128))

        parts = StellarInt256Parts(hi_hi=-1, hi_lo=0xFFFFFFFFFFFFFFFF, lo_hi=0, lo_lo=0)
        self.assertEqual(_format_i256(parts), str(-(2**128)))

        parts = StellarInt256Parts(hi_hi=1, hi_lo=0, lo_hi=0, lo_lo=0)
        self.assertEqual(_format_i256(parts), str(2**192))

        parts = StellarInt256Parts(hi_hi=-1, hi_lo=0, lo_hi=0, lo_lo=0)
        self.assertEqual(_format_i256(parts), str(-(2**192)))

        parts = StellarInt256Parts(
            hi_hi=0x7FFFFFFFFFFFFFFF,
            hi_lo=0xFFFFFFFFFFFFFFFF,
            lo_hi=0xFFFFFFFFFFFFFFFF,
            lo_lo=0xFFFFFFFFFFFFFFFF,
        )
        self.assertEqual(_format_i256(parts), str(2**255 - 1))

        parts = StellarInt256Parts(hi_hi=-0x8000000000000000, hi_lo=0, lo_hi=0, lo_lo=0)
        self.assertEqual(_format_i256(parts), str(-(2**255)))


if __name__ == "__main__":
    unittest.main()
