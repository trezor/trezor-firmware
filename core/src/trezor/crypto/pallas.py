"""Curve for Zcash cryptography."""

from trezor import utils

if utils.ZCASH_SHIELDED:
    from trezorpallas import (  # noqa: F401
        Fp,
        Point,
        Scalar,
        group_hash,
        scalar_from_i64,
        to_base,
        to_scalar,
        Generators,
    )
    generators = Generators()  # init generators
