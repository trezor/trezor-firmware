from typing import TYPE_CHECKING

from trezor import io
from trezor.wire.errors import DataError, FirmwareError

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import NoReturn

    from trezor.ui import ProgressLayout
    from trezorapp import AppImage

    from apps.common.keychain import Keychain
    from apps.common.paths import PathSchema

# IPC services between Core and a running external app
SERVICE_WIRE = 0
SERVICE_WIRE_ERROR = 1
SERVICE_UI = 2
SERVICE_PROGRESS = 3
SERVICE_CRYPTO = 4
SERVICE_LIFECYCLE = 5

# message id on `SERVICE_LIFECYCLE`: the app must exit as soon as it can
LIFECYCLE_ABORT = 0

# message id of a Core reply reporting a failed request
MSG_ID_ERROR = 0xFFFF

_SLIP24_NAMESPACE = [b"SLIP-0024"]


class ApplicationError(FirmwareError):
    """The app crashed or broke the lifecycle protocol."""


def describe(exception: BaseException) -> str:
    """Text of `exception`, falling back to its type when it has none."""
    # `wire.Error` keeps its text in `.message`, its `str()` is empty
    message = getattr(exception, "message", None) or str(exception)
    return message or exception.__class__.__name__


class Session:
    """State of one run of an external app."""

    def __init__(
        self,
        image: AppImage,
        instance_id: int,
        curves: list[str],
        schemas: list[PathSchema],
    ) -> None:
        self.image = image
        self.instance_id = instance_id
        self.task_id = image.task_id()
        # curves allowed by the app's manifest
        self.curves = curves
        self.schemas = schemas
        # keychains created so far, by curve
        self.keychains: dict[str, Keychain] = {}
        # progress layout opened by the app via `SERVICE_PROGRESS`
        self.progress: ProgressLayout | None = None
        # The app reports work in its own units; the count and the fill are ours.
        self.progress_total = 0
        self.progress_done = 0
        # whether the app answered the host's last message
        self.response_sent = False
        # set once Core killed the app
        self.stopped = False
        # set once the app was killed because of an error
        self.dead = False

    @property
    def app_id(self) -> str:
        """The app's identity, its image ID (`<package>.<domain>`): the prefix
        of every step it asks for. A package name alone could be shared by two
        vendors."""
        return self.image.id()

    async def keychain(self, curve: str) -> Keychain:
        """Keychain of the app's paths on `curve`, if the app is allowed to use it."""
        from apps.common.keychain import get_keychain

        if curve not in self.curves:
            raise DataError(f"Curve {curve} not allowed")
        keychain = self.keychains.get(curve)
        if keychain is None:
            keychain = await get_keychain(curve, self.schemas, [_SLIP24_NAMESPACE])
            self.keychains[curve] = keychain
        return keychain

    def send(self, service: int, message_id: int, data: AnyBytes) -> None:
        io.ipc_send(self.task_id, service, message_id, data)

    def stop(self) -> None:
        self.stopped = True
        self.image.stop()

    def die(self, exception: Exception) -> NoReturn:
        self.dead = True
        if __debug__:
            log.error(__name__, f"Task died due to exception: {exception}")
        self.stop()
        raise exception
