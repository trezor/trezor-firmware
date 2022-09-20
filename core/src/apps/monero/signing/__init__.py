from trezor.wire import DataError


class Error(DataError):
    pass


class ChangeAddressError(DataError):
    pass


class NotEnoughOutputsError(DataError):
    pass


class RctType:
    """
    There are several types of monero Ring Confidential Transactions
    like RCTTypeFull and RCTTypeSimple, but currently we use only RCTTypeBulletproofPlus
    """

    RCTTypeBulletproofPlus = 6
