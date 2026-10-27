from typing import TYPE_CHECKING

from trezor import io

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import NoReturn

    from trezor.ui import ProgressLayout
    from trezorapp import AppImage

    from apps.common.paths import PathSchema

# IPC services between Core and a running external app
SERVICE_WIRE_START = 0
SERVICE_WIRE_CONTINUE = 1
SERVICE_WIRE_END = 2
SERVICE_WIRE_ERROR = 3
SERVICE_UI = 4
SERVICE_PROGRESS = 5
SERVICE_CRYPTO = 6

# message id of a Core reply reporting a failed request
MSG_ID_ERROR = 0xFFFF


def describe(exception: BaseException) -> str:
    """Text of `exception`, falling back to its type when it has none."""
    # `wire.Error` keeps its text in `.message`, its `str()` is empty
    message = getattr(exception, "message", None) or str(exception)
    return message or exception.__class__.__name__


class Session:
    """State of a single `ExtAppMessage` exchange with a running external app."""

    def __init__(
        self,
        image: AppImage,
        curve: str,
        schemas: list[PathSchema],
    ) -> None:
        self.image = image
        self.task_id = image.task_id()
        self.curve = curve
        self.schemas = schemas
        # progress layout opened by the app via `SERVICE_PROGRESS`
        self.progress: ProgressLayout | None = None
        # set once the app was stopped because of an error
        self.dead = False

    def send(self, service: int, message_id: int, data: AnyBytes) -> None:
        io.ipc_send(self.task_id, service, message_id, data)

    def die(self, exception: Exception) -> NoReturn:
        self.dead = True
        if __debug__:
            log.error(__name__, f"Task died due to exception: {exception}")
        self.image.stop()
        raise exception
