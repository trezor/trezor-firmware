from trezor.enums import FailureType as F

# XXX this rename is also required so that `import errors.*` work in wire/__init__.py
# Otherwise, although the revealed type of FailureType is the same in here and there,
# mypy will complain that one is a module and other is Type[FailureType]


class Error(Exception):
    def __init__(self, code: F, message: str) -> None:
        super().__init__()
        self.code = code
        self.message = message


class UnexpectedMessage(Error):
    def __init__(self, message: str) -> None:
        super().__init__(F.UnexpectedMessage, message)


class ButtonExpected(Error):
    def __init__(self, message: str) -> None:
        super().__init__(F.ButtonExpected, message)


class DataError(Error):
    def __init__(self, message: str) -> None:
        super().__init__(F.DataError, message)


class ActionCancelled(Error):
    def __init__(self, message: str = "Cancelled") -> None:
        super().__init__(F.ActionCancelled, message)


class PinExpected(Error):
    def __init__(self, message: str) -> None:
        super().__init__(F.PinExpected, message)


class PinCancelled(Error):
    def __init__(self, message: str = "PIN entry cancelled") -> None:
        super().__init__(F.PinCancelled, message)


class PinInvalid(Error):
    def __init__(self, message: str = "PIN invalid") -> None:
        super().__init__(F.PinInvalid, message)


class InvalidSignature(Error):
    def __init__(self, message: str) -> None:
        super().__init__(F.InvalidSignature, message)


class ProcessError(Error):
    def __init__(self, message: str) -> None:
        super().__init__(F.ProcessError, message)


class NotEnoughFunds(Error):
    def __init__(self, message: str) -> None:
        super().__init__(F.NotEnoughFunds, message)


class NotInitialized(Error):
    def __init__(self, message: str) -> None:
        super().__init__(F.NotInitialized, message)


class PinMismatch(Error):
    def __init__(self, message: str) -> None:
        super().__init__(F.PinMismatch, message)


class WipeCodeMismatch(Error):
    def __init__(self, message: str) -> None:
        super().__init__(F.WipeCodeMismatch, message)


class InvalidSession(Error):
    def __init__(self, message: str = "Invalid session") -> None:
        super().__init__(F.InvalidSession, message)


class FirmwareError(Error):
    def __init__(self, message: str) -> None:
        super().__init__(F.FirmwareError, message)
