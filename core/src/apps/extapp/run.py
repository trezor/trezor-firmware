from trezor.messages import ExtAppRun, ExtAppResult, Failure


async def run(msg: ExtAppRun) -> ExtAppResult | Failure:
    from trezor.ui.layouts import interact
    from trezor import io, loop, app
    import trezorui_api

    # Use provided hash, fn_id, and data from the message
    # For now, we'll spawn using the hash as the app identifier
    # In a real implementation, you'd look up the loaded app by hash
    app_hash = msg.hash or b""
    fn_id = msg.fn_id or 0
    call_data = msg.data or b""

    # TODO: Verify app_hash matches a loaded app before spawning
    task = app.spawn_task(app_hash)

    if task.is_running() is False:
        return Failure(message="Failed to spawn external app task")

    while True:
        msg = await loop.wait(io.IPC2_EVENT | io.POLL_READ)

        if msg.fn() == 0:
            result = await interact(
                trezorui_api.process_ipc_message(data=msg.data()),
                None,
                raise_on_cancel=None,
            )
            # Serialize the result into a compact binary response
            resp = trezorui_api.serialize_ui_result(result=result)

        elif msg.fn() == 1:
            # Simple pong response (tag 0x10, no payload)
            resp = msg.data()
        elif msg.fn() == 2:
            task.unload()
            # Return both message and serialized result data
            return ExtAppResult(data=b"\n\x01a")

        else:
            # Error tag 0xFF for unknown function
            raise Exception("Unknown IPC function")
        io.ipc_send(msg.remote(), msg.fn(), resp)
        msg.free()
