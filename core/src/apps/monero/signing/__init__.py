from trezor import wire


class Error(wire.DataError):
    pass


class ChangeAddressError(wire.DataError):
    pass


class NotEnoughOutputsError(wire.DataError):
    pass


class RctType:
    """
    There are several types of monero Ring Confidential Transactions
    like RCTTypeFull and RCTTypeSimple but currently we use only CLSAG
    and RCTTypeBulletproofPlus
    """

    CLSAG = 5
    RCTTypeBulletproofPlus = 6
