from typing import TYPE_CHECKING

import trezorui_api
from trezor.ui.layouts.common import interact

from .session import SERVICE_UI

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import IpcMessage

    from .session import Session


async def handle(session: Session, msg: IpcMessage) -> None:
    """Show the layout requested by the app and send it the user's result."""
    try:
        layout_obj, br_code, br_name = trezorui_api.process_ipc_message(
            data=bytes(msg.data)
        )
    except Exception:
        session.die("Invalid UI request")
    result = await interact(layout_obj, br_name, br_code, raise_on_cancel=None)
    if __debug__:
        log.debug(__name__, f"UI interaction result: {result}")

    try:
        data = trezorui_api.serialize_ui_result(result=result)
    except Exception:
        session.die("Failed to serialize UI result")
    session.send(SERVICE_UI, 0, data)
