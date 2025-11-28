import ustruct
from micropython import const
from typing import TYPE_CHECKING

from storage.cache import get_sessionless_cache
from storage import cache_common as cc

from trezor.ui.layouts import interact
from trezor import io, loop, app
from trezor.wire import context
from trezor.wire.errors import DataError
import trezorui_api
from trezor.messages import ExtAppMessage, ExtAppResponse

if TYPE_CHECKING:
    from typing import NoReturn
    from trezorio import IpcMessage

_SYSTASK_ID_EXTAPP = const(2)

_SERVICE_LIFECYCLE = const(0)
_SERVICE_UI = const(1)
_SERVICE_WIRE_START = const(2)
_SERVICE_WIRE_CONTINUE = const(3)
_SERVICE_WIRE_END = const(4)


def fn_id(service: int, message_id: int) -> int:
    print("service:", service, "message_id:", message_id)
    print("fn_id:", (service << 16) | (message_id & 0xFFFF))
    return (service << 16) | (message_id & 0xFFFF)


def from_fn_id(fn_id: int) -> tuple[int, int]:
    return ((fn_id >> 16) & 0xFFFF, fn_id & 0xFFFF)


async def run(request: ExtAppMessage) -> ExtAppResponse:
    if request.message_id > 0xFFFF:
        raise DataError("Invalid message ID.")

    instance_ids = get_sessionless_cache().get(cc.APP_EXTAPP_IDS)
    if instance_ids is None:
        raise DataError(f"Invalid instance ID: {request.instance_id}")
    task_id, instance_id = ustruct.unpack("<BI", instance_ids)
    if instance_id != request.instance_id:
        raise DataError(f"Invalid instance ID: {request.instance_id}")

    task = app.AppTask(task_id)
    if not task.is_running():
        raise DataError(f"Task not running: {request.instance_id}")

    io.ipc_send(
        _SYSTASK_ID_EXTAPP, fn_id(_SERVICE_WIRE_START, request.message_id), request.data
    )

    def die(exception: Exception) -> NoReturn:
        task.unload()
        raise exception

    while True:
        if not task.is_running():
            raise DataError(f"Task stopped: {request.instance_id}")
        try:
            msg: IpcMessage = await loop.wait(io.IPC2_EVENT | io.POLL_READ, timeout_ms=1000)
        except loop.Timeout:
            die(DataError("Timeout waiting for message"))

        service, message_id = from_fn_id(msg.fn)

        if service == _SERVICE_UI:
            result = await interact(
                trezorui_api.process_ipc_message(data=bytes(msg.data)),
                None,
                raise_on_cancel=None,
            )
            # Serialize the result into a compact binary response
            resp = trezorui_api.serialize_ui_result(result=result)
            io.ipc_send(_SYSTASK_ID_EXTAPP, fn_id(_SERVICE_UI, 0), resp)

        elif service == _SERVICE_WIRE_CONTINUE:
            # usb request/ack
            response = ExtAppResponse(
                message_id=message_id, data=msg.data, finished=False
            )
            ack = await context.call(response, ExtAppMessage)
            if ack.message_id > 0xFFFF:
                die(DataError("Invalid message ID."))
            io.ipc_send(
                _SYSTASK_ID_EXTAPP,
                fn_id(_SERVICE_WIRE_CONTINUE, ack.message_id),
                ack.data,
            )

        elif service == _SERVICE_WIRE_END:
            # usb final message
            response = ExtAppResponse(
                message_id=message_id, data=msg.data, finished=True
            )
            task.unload()
            return response

        else:
            die(RuntimeError("Unknown IPC function"))
