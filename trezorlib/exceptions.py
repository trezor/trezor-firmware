class TrezorException(Exception):
    pass


class TrezorFailure(TrezorException):
    def __init__(self, failure):
        self.failure = failure
        # TODO: this is backwards compatibility with tests. it should be changed
        super().__init__(self.failure.code, self.failure.message)

    def __str__(self):
        from .messages import FailureType

        types = {
            getattr(FailureType, name): name
            for name in dir(FailureType)
            if not name.startswith("_")
        }
        if self.failure.message is not None:
            return "{}: {}".format(types[self.failure.code], self.failure.message)
        else:
            return types[self.failure.code]


class PinException(TrezorException):
    pass


class Cancelled(TrezorException):
    pass
