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
    like RCTTypeFull and RCTTypeSimple but currently we use only Bulletproof2
    """

    Bulletproof2 = 4
    CLSAG = 5
