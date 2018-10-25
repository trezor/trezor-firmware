from trezor import wire


class Error(wire.DataError):
    pass


class ChangeAddressError(wire.DataError):
    pass


class NotEnoughOutputsError(wire.DataError):
    pass


class RctType:
    """
    There are two types of monero Ring Confidential Transactions:
    1. RCTTypeFull = 1 (used if num_inputs == 1)
    2. RCTTypeSimple = 2 (for num_inputs > 1)

    There is actually also RCTTypeNull but we ignore that one.
    """

    Full = 1
    Simple = 2


class RsigType:
    """
    Range signature types

    There are four types of range proofs/signatures in official Monero:
    1. RangeProofBorromean = 0
    2. RangeProofBulletproof = 1
    3. RangeProofMultiOutputBulletproof = 2
    4. RangeProofPaddedBulletproof = 3

    We simplify all the bulletproofs into one.
    """

    Borromean = 0
    Bulletproof = 1


def get_monero_rct_type(rct_type, rsig_type):
    """
    This converts our internal representation of RctType and RsigType
    into what is used in Monero:
    - Null = 0
    - Full = 1
    - Simple = 2
    - Simple/Full with bulletproof = 3
    """
    if rsig_type == RsigType.Bulletproof:
        return 3  # Bulletproofs
    if rct_type == RctType.Simple:
        return 2  # Simple
    else:
        return 1  # Full
