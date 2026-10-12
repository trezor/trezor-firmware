from typing import TYPE_CHECKING

import trezorui_api
from trezor import ui, workflow
from trezor.enums import ButtonRequestType
from trezor.wire.errors import DataError

from .session import SERVICE_UI

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import IpcMessage
    from typing import Any

    from .session import Session


async def handle(session: Session, msg: IpcMessage) -> None:
    """Show the block the app asked for and send the app the person's answer."""
    try:
        result = await _show_block(bytes(msg.data))
    except DataError as e:
        session.die(e)
    if __debug__:
        log.debug(__name__, f"UI interaction result: {result}")

    def send(data: bytes) -> None:
        session.send(SERVICE_UI, 0, data)

    try:
        trezorui_api.send_ui_result(result=result, ipc_cb=send)
    except Exception as e:
        session.die(DataError(f"Cannot send the screen's result: {e}"))


async def _show_new_layout(layout_obj: Any, br_name: str) -> tuple[ui.Layout, Any]:
    """Show a freshly built layout, and wait for the answer.

    Returns the layout as well, so that a caller which means to show it again
    can keep it instead of paying for a second one.
    """
    # The body of `interact()`, unrolled because the layout itself is needed
    # and `interact()` only hands back the result.
    workflow.close_others()
    layout = ui.Layout(layout_obj)
    layout.start()
    # Every app step is `Other`; its name carries the meaning.
    layout.put_button_request((ButtonRequestType.Other, br_name))
    return layout, await layout.get_result()


async def _show_block(data: bytes) -> Any:
    """Show one block of an app and return its final answer.

    The request carries the block's extras, so the block's menu is walked here:
    the person can open the menu, look at extras and come back as often as they
    like, and only the decision goes back to the app.
    """
    try:
        layout_obj, br_name = trezorui_api.process_ipc_message(data=data)
    except Exception as e:
        # The request cannot be drawn. Answering would leave the app waiting on
        # a screen that never existed, so the app stops.
        raise DataError(f"Cannot show the app's screen: {e}")
    layout, result = await _show_new_layout(layout_obj, br_name)
    while result is trezorui_api.INFO:
        result = await _walk_extras(data, br_name)
        if result is None:
            # Back to the block, as the person left it.
            result = await _run_layout(layout)
    return result


async def _walk_extras(data: bytes, br_name: str) -> Any:
    """Show the block's menu of extras until the person leaves it.

    Returns `CANCELLED` when they refused the block from the menu (the way out
    some models keep there), or `None` to go back to the block.
    """
    try:
        menu_obj = trezorui_api.process_ipc_extra(data=data)
    except Exception as e:
        raise DataError(f"Cannot show the app's menu: {e}")
    menu, choice = await _show_new_layout(menu_obj, br_name + "/menu")
    while isinstance(choice, int):
        try:
            extra_obj = trezorui_api.process_ipc_extra(data=data, index=choice)
        except Exception as e:
            raise DataError(f"Cannot show the app's extra: {e}")
        # Leaving the extra comes back to the menu, on the entry it was.
        await _show_new_layout(extra_obj, br_name + "/details")
        choice = await _run_layout(menu)
    if choice is trezorui_api.CANCELLED:
        return choice
    return None


async def _run_layout(layout: ui.Layout) -> Any:
    """Show a layout that is already built, and wait for the person to answer.

    The layout keeps whatever state it had — which page it was on, how far it
    was scrolled — because it is started again rather than constructed again.
    """
    # Same courtesy `interact()` does: nobody else should be drawing.
    workflow.close_others()
    # The person has seen this screen before, so it should return rather than
    # arrive.
    layout.should_resume = True
    layout.start()
    return await layout.get_result()
