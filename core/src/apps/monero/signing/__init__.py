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


def get_monero_rct_type(bp_version=1):
    """
    Returns transaction RctType according to the BP version.
    Only HP9+ is supported, thus only Simple variant is concerned.
    """
    if bp_version == 1:
        return 3  # TxRctType.Bulletproof
    elif bp_version == 2:
        return 4  # TxRctType.Bulletproof2
    else:
        raise ValueError("Unsupported BP version")
