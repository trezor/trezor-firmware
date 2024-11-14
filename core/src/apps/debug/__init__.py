if not __debug__:
    from trezor.utils import halt

    halt("debug mode inactive")

if __debug__:
    import utime
    from micropython import const
    from typing import TYPE_CHECKING

    import trezorui2
    from storage import debug as storage
    from trezor import io, log, loop, ui, utils, wire, workflow
    from trezor.enums import DebugWaitType, MessageType
    from trezor.messages import Success
    from trezor.ui import display

    if TYPE_CHECKING:
        from typing import Any, Awaitable, Callable

        from trezor.enums import DebugButton, DebugPhysicalButton, DebugSwipeDirection
        from trezor.messages import (
            DebugLinkDecision,
            DebugLinkEraseSdCard,
            DebugLinkGetState,
            DebugLinkOptigaSetSecMax,
            DebugLinkRecordScreen,
            DebugLinkReseedRandom,
            DebugLinkState,
        )
        from trezor.ui import Layout
        from trezor.wire import WireInterface, context

        Handler = Callable[[Any], Awaitable[Any]]

    layout_change_box = loop.mailbox()

    DEBUG_CONTEXT: context.Context | None = None

    REFRESH_INDEX = 0

    _DEADLOCK_SLEEP_MS = const(3000)
    _DEADLOCK_DETECT_SLEEP = loop.sleep(_DEADLOCK_SLEEP_MS)

    def screenshot() -> bool:
        if storage.save_screen:
            # Starting with "refresh00", allowing for 100 emulator restarts
            # without losing the order of the screenshots based on filename.
            display.save(
                storage.save_screen_directory + f"/refresh{REFRESH_INDEX:0>2}-"
            )
            return True
        return False

    def notify_layout_change(layout: Layout | None) -> None:
        layout_change_box.put(layout, replace=True)

    def layout_is_ready() -> bool:
        layout = ui.CURRENT_LAYOUT
        return isinstance(layout, ui.Layout) and layout.is_layout_attached()

    def wait_until_layout_is_running(timeout: int | None = _DEADLOCK_SLEEP_MS) -> Awaitable[None]:  # type: ignore [awaitable-return-type]
        start = utime.ticks_ms()
        layout_change_box.clear()
        while not layout_is_ready():
            yield layout_change_box  # type: ignore [awaitable-return-type]
            now = utime.ticks_ms()
            if timeout and utime.ticks_diff(now, start) > timeout:
                raise wire.FirmwareError(
                    "layout deadlock detected (did you send a ButtonAck?)"
                )

    async def return_layout_change(
        ctx: wire.context.Context, detect_deadlock: bool = False
    ) -> None:
        # set up the wait
        storage.layout_watcher = True

        # wait for layout change
        while True:
            if not detect_deadlock or not layout_change_box.is_empty():
                # short-circuit if there is a result already waiting
                next_layout = await layout_change_box
            else:
                next_layout = await loop.race(layout_change_box, _DEADLOCK_DETECT_SLEEP)

            if isinstance(next_layout, int):
                # sleep result from the deadlock detector
                raise wire.FirmwareError("layout deadlock detected")

            if next_layout is None:
                # we are reading the "layout ended" event, spin once more to grab the
                # "new layout started" event
                continue

            if layout_is_ready():
                break

        assert ui.CURRENT_LAYOUT is next_layout

        # send the message and reset the wait
        storage.layout_watcher = False
        await ctx.write(_state())

    async def _layout_click(x: int, y: int, hold_ms: int = 0) -> None:
        assert isinstance(ui.CURRENT_LAYOUT, ui.Layout)
        ui.CURRENT_LAYOUT._event(
            ui.CURRENT_LAYOUT.layout.touch_event, io.TOUCH_START, x, y
        )

        if hold_ms:
            await loop.sleep(hold_ms)
            workflow.idle_timer.touch()

        if not layout_is_ready():
            return
        ui.CURRENT_LAYOUT._event(
            ui.CURRENT_LAYOUT.layout.touch_event, io.TOUCH_END, x, y
        )

    async def _layout_press_button(
        debug_btn: DebugPhysicalButton, hold_ms: int = 0
    ) -> None:
        from trezor.enums import DebugPhysicalButton

        buttons = []

        if debug_btn == DebugPhysicalButton.LEFT_BTN:
            buttons.append(io.BUTTON_LEFT)
        elif debug_btn == DebugPhysicalButton.RIGHT_BTN:
            buttons.append(io.BUTTON_RIGHT)
        elif debug_btn == DebugPhysicalButton.MIDDLE_BTN:
            buttons.append(io.BUTTON_LEFT)
            buttons.append(io.BUTTON_RIGHT)

        assert isinstance(ui.CURRENT_LAYOUT, ui.Layout)
        for btn in buttons:
            ui.CURRENT_LAYOUT._event(
                ui.CURRENT_LAYOUT.layout.button_event, io.BUTTON_PRESSED, btn
            )

        if hold_ms:
            await loop.sleep(hold_ms)
            workflow.idle_timer.touch()

        if not layout_is_ready():
            return
        for btn in buttons:
            ui.CURRENT_LAYOUT._event(
                ui.CURRENT_LAYOUT.layout.button_event, io.BUTTON_RELEASED, btn
            )

    if utils.USE_TOUCH:

        async def _layout_swipe(direction: DebugSwipeDirection) -> None:  # type: ignore [obscured by a declaration of the same name]
            from trezor.enums import DebugSwipeDirection

            orig_x = orig_y = 120
            off_x, off_y = {
                DebugSwipeDirection.UP: (0, -30),
                DebugSwipeDirection.DOWN: (0, 30),
                DebugSwipeDirection.LEFT: (-30, 0),
                DebugSwipeDirection.RIGHT: (30, 0),
            }[direction]

            assert isinstance(ui.CURRENT_LAYOUT, ui.Layout)
            for event, x, y in (
                (io.TOUCH_START, orig_x, orig_y),
                (io.TOUCH_MOVE, orig_x + 1 * off_x, orig_y + 1 * off_y),
                (io.TOUCH_END, orig_x + 2 * off_x, orig_y + 2 * off_y),
            ):
                ui.CURRENT_LAYOUT._event(
                    ui.CURRENT_LAYOUT.layout.touch_event, event, x, y
                )

    elif utils.USE_BUTTON:

        def _layout_swipe(direction: DebugSwipeDirection) -> Awaitable[None]:
            from trezor.enums import DebugPhysicalButton, DebugSwipeDirection

            if direction == DebugSwipeDirection.UP:
                button = DebugPhysicalButton.RIGHT_BTN
            elif direction == DebugSwipeDirection.DOWN:
                button = DebugPhysicalButton.LEFT_BTN
            else:
                raise RuntimeError  # unsupported swipe direction on TR

            return _layout_press_button(button)

    else:
        raise RuntimeError  # No way to swipe with no buttons and no touches

    async def _layout_event(button: DebugButton) -> None:
        from trezor.enums import DebugButton

        assert isinstance(ui.CURRENT_LAYOUT, ui.Layout)
        if button == DebugButton.NO:
            ui.CURRENT_LAYOUT._emit_message(trezorui2.CANCELLED)
        elif button == DebugButton.YES:
            ui.CURRENT_LAYOUT._emit_message(trezorui2.CONFIRMED)
        elif button == DebugButton.INFO:
            ui.CURRENT_LAYOUT._emit_message(trezorui2.INFO)
        else:
            raise RuntimeError("Invalid DebugButton")

    async def dispatch_DebugLinkDecision(
        msg: DebugLinkDecision,
    ) -> DebugLinkState | None:
        from trezor import ui, workflow

        workflow.idle_timer.touch()

        x = msg.x  # local_cache_attribute
        y = msg.y  # local_cache_attribute

        await wait_until_layout_is_running()
        assert isinstance(ui.CURRENT_LAYOUT, ui.Layout)
        layout_change_box.clear()

        try:
            # click on specific coordinates, with possible hold
            if x is not None and y is not None:
                await _layout_click(x, y, msg.hold_ms or 0)
            # press specific button
            elif msg.physical_button is not None:
                await _layout_press_button(msg.physical_button, msg.hold_ms or 0)
            elif msg.swipe is not None:
                await _layout_swipe(msg.swipe)
            elif msg.button is not None:
                await _layout_event(msg.button)
            elif msg.input is not None:
                ui.CURRENT_LAYOUT._emit_message(msg.input)
            else:
                raise RuntimeError("Invalid DebugLinkDecision message")

        except ui.Shutdown:
            # Shutdown should be raised if the layout is supposed to stop after
            # processing the event. In that case, we need to yield to give the layout
            # callers time to finish their jobs. We want to make sure that the handling
            # does not continue until the event is truly processed.
            result = await layout_change_box
            assert result is None

        # If no exception was raised, the layout did not shut down. That means that it
        # just updated itself. The update is already live for the caller to retrieve.

    def _state() -> DebugLinkState:
        from trezor.messages import DebugLinkState

        from apps.common import mnemonic, passphrase

        tokens = []

        def callback(*args: str) -> None:
            tokens.extend(args)

        if ui.CURRENT_LAYOUT is not None:
            ui.CURRENT_LAYOUT.layout.trace(callback)

        return DebugLinkState(
            mnemonic_secret=mnemonic.get_secret(),
            mnemonic_type=mnemonic.get_type(),
            passphrase_protection=passphrase.is_enabled(),
            reset_entropy=storage.reset_internal_entropy,
            tokens=tokens,
        )

    async def dispatch_DebugLinkGetState(
        msg: DebugLinkGetState,
    ) -> DebugLinkState | None:
        if msg.wait_layout == DebugWaitType.IMMEDIATE:
            return _state()

        assert DEBUG_CONTEXT is not None
        if msg.wait_layout == DebugWaitType.NEXT_LAYOUT:
            layout_change_box.clear()
            return await return_layout_change(DEBUG_CONTEXT, detect_deadlock=False)

        # default behavior: msg.wait_layout == DebugWaitType.CURRENT_LAYOUT
        if not layout_is_ready():
            return await return_layout_change(DEBUG_CONTEXT, detect_deadlock=True)
        else:
            return _state()

    async def dispatch_DebugLinkRecordScreen(msg: DebugLinkRecordScreen) -> Success:
        if msg.target_directory:
            # Ensure we consistently start at a layout, instead of randomly sometimes
            # hitting the pause between layouts and rendering the "upcoming" one.
            await wait_until_layout_is_running()

            # In case emulator is restarted but we still want to record screenshots
            # into the same directory as before, we need to increment the refresh index,
            # so that the screenshots are not overwritten.
            global REFRESH_INDEX
            REFRESH_INDEX = msg.refresh_index
            storage.save_screen_directory = msg.target_directory
            storage.save_screen = True

            # force repaint current layout, in order to take an initial screenshot
            # (doing it this way also clears the red square, because the repaint is
            # happening with screenshotting already enabled)
            assert isinstance(ui.CURRENT_LAYOUT, ui.Layout)
            ui.CURRENT_LAYOUT.request_complete_repaint()
            ui.CURRENT_LAYOUT._paint()

        else:
            storage.save_screen = False
            display.clear_save()  # clear C buffers

        return Success()

    async def dispatch_DebugLinkReseedRandom(msg: DebugLinkReseedRandom) -> Success:
        if msg.value is not None:
            from trezor.crypto import random

            random.reseed(msg.value)
        return Success()

    async def dispatch_DebugLinkEraseSdCard(msg: DebugLinkEraseSdCard) -> Success:
        from trezor import io

        sdcard = io.sdcard  # local_cache_attribute

        try:
            sdcard.power_on()
            if msg.format:
                io.fatfs.mkfs()
            else:
                # trash first 1 MB of data to destroy the FAT filesystem
                assert sdcard.capacity() >= 1024 * 1024
                empty_block = bytes([0xFF] * sdcard.BLOCK_SIZE)
                for i in range(1024 * 1024 // sdcard.BLOCK_SIZE):
                    sdcard.write(i, empty_block)

        except OSError:
            raise wire.ProcessError("SD card operation failed")
        finally:
            sdcard.power_off()
        return Success()

    async def dispatch_DebugLinkOptigaSetSecMax(
        msg: DebugLinkOptigaSetSecMax,
    ) -> Success:
        if utils.USE_OPTIGA:
            from trezor.crypto import optiga

            optiga.set_sec_max()
            return Success()
        else:
            raise wire.UnexpectedMessage("Optiga not supported")

    async def _no_op(_msg: Any) -> Success:
        return Success()

    WIRE_BUFFER_DEBUG = bytearray(1024)

    async def handle_session(iface: WireInterface) -> None:
        from trezor import protobuf, wire
        from trezor.wire import codec_v1, context

        global DEBUG_CONTEXT

        DEBUG_CONTEXT = ctx = context.Context(iface, WIRE_BUFFER_DEBUG)

        if storage.layout_watcher:
            try:
                await return_layout_change(ctx)
            except Exception as e:
                log.exception(__name__, e)

        while True:
            try:
                try:
                    msg = await ctx.read_from_wire()
                except codec_v1.CodecError as exc:
                    log.exception(__name__, exc)
                    await ctx.write(wire.failure(exc))
                    continue

                req_type = None
                try:
                    req_type = protobuf.type_for_wire(msg.type)
                    msg_type = req_type.MESSAGE_NAME
                except Exception:
                    msg_type = f"{msg.type} - unknown message type"
                log.debug(
                    __name__,
                    "%d receive: <%s>",
                    ctx.iface.iface_num(),
                    msg_type,
                )

                if msg.type not in WORKFLOW_HANDLERS:
                    await ctx.write(wire.unexpected_message())
                    continue

                elif req_type is None:
                    # Message type is in workflow handlers but not in protobuf
                    # definitions. This indicates a deprecated message.
                    # We put a no-op handler for those messages.
                    # XXX return a Failure here?
                    await ctx.write(Success())
                    continue

                req_msg = wire.wrap_protobuf_load(msg.data, req_type)
                try:
                    res_msg = await WORKFLOW_HANDLERS[msg.type](req_msg)
                except Exception as exc:
                    # Log and ignore, never die.
                    log.exception(__name__, exc)
                    res_msg = wire.failure(exc)

                if res_msg is not None:
                    await ctx.write(res_msg)

            except Exception as exc:
                # Log and try again. This should only happen for USB errors and we
                # try to stay robust in such case.
                log.exception(__name__, exc)

    WORKFLOW_HANDLERS: dict[int, Handler] = {
        MessageType.DebugLinkDecision: dispatch_DebugLinkDecision,
        MessageType.DebugLinkGetState: dispatch_DebugLinkGetState,
        MessageType.DebugLinkReseedRandom: dispatch_DebugLinkReseedRandom,
        MessageType.DebugLinkRecordScreen: dispatch_DebugLinkRecordScreen,
        MessageType.DebugLinkEraseSdCard: dispatch_DebugLinkEraseSdCard,
        MessageType.DebugLinkOptigaSetSecMax: dispatch_DebugLinkOptigaSetSecMax,
        MessageType.DebugLinkWatchLayout: _no_op,
        MessageType.DebugLinkResetDebugEvents: _no_op,
    }

    def boot() -> None:
        import usb

        loop.schedule(handle_session(usb.iface_debug))
