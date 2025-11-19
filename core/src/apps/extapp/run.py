import ustruct
from micropython import const

from storage.cache import get_sessionless_cache
from storage import cache_common as cc

from trezor.ui.layouts import interact
from trezor import io, loop, app
from trezor.wire import context
from trezor.wire.errors import DataError
import trezorui_api
from trezor.messages import ExtAppMessage, ExtAppResponse

_SYSTASK_ID_EXTAPP = const(2)


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

    fn_id = 0x0001_0000 | (request.message_id & 0xFFFF)
    io.ipc_send(_SYSTASK_ID_EXTAPP, fn_id, request.data)
    while True:
        msg = await loop.wait(io.IPC2_EVENT | io.POLL_READ)
        fn_id = msg.fn()
        fn_id_hi = fn_id >> 16
        fn_id_lo = fn_id & 0xFFFF

        if fn_id_hi == 0:
            result = await interact(
                trezorui_api.process_ipc_message(data=msg.data()),
                None,
                raise_on_cancel=None,
            )
            # Serialize the result into a compact binary response
            resp = trezorui_api.serialize_ui_result(result=result)
            io.ipc_send(_SYSTASK_ID_EXTAPP, fn_id, resp)

        elif fn_id_hi == 1:
            # usb request/ack
            response = ExtAppResponse(
                message_id=fn_id_lo, data=msg.data(), finished=False
            )
            ack = await context.call(response, ExtAppMessage)
            if ack.message_id > 0xFFFF:
                raise DataError("Invalid message ID.")
            fn_id = 0x0002_0000 | (ack.message_id & 0xFFFF)
            io.ipc_send(_SYSTASK_ID_EXTAPP, fn_id, ack.data)

        elif fn_id_hi == 2:
            # usb final message
            response = ExtAppResponse(
                message_id=fn_id_lo, data=msg.data(), finished=True
            )
            task.unload()
            return response

        else:
            task.unload()
            # Error tag 0xFF for unknown function
            raise RuntimeError("Unknown IPC function")
