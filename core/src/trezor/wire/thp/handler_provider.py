from typing import TYPE_CHECKING

from trezor import protobuf
from trezor.enums import MessageType
from trezor.wire.errors import UnexpectedMessage

if TYPE_CHECKING:
    from typing import Any, Callable, Coroutine

    from trezor.messages import Features, GetFeatures


def find_management_session_message_handler(
    msg_type: int,
) -> Callable[[Any], Coroutine[Any, Any, protobuf.MessageType]]:
    if msg_type is MessageType.ThpCreateNewSession:
        from apps.thp.create_session import create_new_session

        return create_new_session
    if msg_type is MessageType.GetFeatures:
        return handle_GetFeatures
    if __debug__:
        if msg_type is MessageType.LoadDevice:
            from apps.debug.load_device import load_device

            return load_device
    raise UnexpectedMessage("There is no handler available for this message")


async def handle_GetFeatures(msg: GetFeatures) -> Features:
    from apps.base import get_features

    return get_features()
