class TrezorException(Exception):
    pass


class PinException(TrezorException):
    pass


class Cancelled(TrezorException):
    pass
