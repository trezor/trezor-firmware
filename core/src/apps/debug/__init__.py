if not __debug__:
    from trezor.utils import halt

    halt("debug mode inactive")

if __debug__:
    from storage import debug as storage

    import trezorui2

    from trezor import log, loop, wire
    from trezor.ui import display
    from trezor.enums import MessageType
    from trezor.messages import (
        DebugLinkLayout,
        Success,
    )

    from apps import workflow_handlers

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from trezor.ui import Layout
        from trezor.messages import (
            DebugLinkDecision,
            DebugLinkEraseSdCard,
            DebugLinkGetState,
            DebugLinkRecordScreen,
            DebugLinkReseedRandom,
            DebugLinkState,
            DebugLinkWatchLayout,
        )

    reset_current_words = loop.chan()
    reset_word_index = loop.chan()

    confirm_chan = loop.chan()
    swipe_chan = loop.chan()
    input_chan = loop.chan()
    confirm_signal = confirm_chan.take
    swipe_signal = swipe_chan.take
    input_signal = input_chan.take

    debuglink_decision_chan = loop.chan()

    layout_change_chan = loop.chan()

    DEBUG_CONTEXT: wire.Context | None = None

    LAYOUT_WATCHER_NONE = 0
    LAYOUT_WATCHER_STATE = 1
    LAYOUT_WATCHER_LAYOUT = 2

    def screenshot() -> bool:
        if storage.save_screen:
            display.save(storage.save_screen_directory + "/refresh-")
            return True
        return False

    def notify_layout_change(layout: Layout) -> None:
        storage.current_content[:] = layout.read_content()
        if storage.watch_layout_changes or layout_change_chan.takers:
            layout_change_chan.publish(storage.current_content)

    async def _dispatch_debuglink_decision(msg: DebugLinkDecision) -> None:
        from trezor.enums import DebugButton, DebugSwipeDirection
        from trezor.ui import (
            Result,
            SWIPE_UP,
            SWIPE_DOWN,
            SWIPE_LEFT,
            SWIPE_RIGHT,
        )

        button = msg.button  # local_cache_attribute
        swipe = msg.swipe  # local_cache_attribute

        if button is not None:
            if button == DebugButton.NO:
                await confirm_chan.put(Result(trezorui2.CANCELLED))
            elif button == DebugButton.YES:
                await confirm_chan.put(Result(trezorui2.CONFIRMED))
            elif button == DebugButton.INFO:
                await confirm_chan.put(Result(trezorui2.INFO))
        if swipe is not None:
            if swipe == DebugSwipeDirection.UP:
                await swipe_chan.put(SWIPE_UP)
            elif swipe == DebugSwipeDirection.DOWN:
                await swipe_chan.put(SWIPE_DOWN)
            elif swipe == DebugSwipeDirection.LEFT:
                await swipe_chan.put(SWIPE_LEFT)
            elif swipe == DebugSwipeDirection.RIGHT:
                await swipe_chan.put(SWIPE_RIGHT)
        if msg.input is not None:
            await input_chan.put(Result(msg.input))

    async def debuglink_decision_dispatcher() -> None:
        while True:
            msg = await debuglink_decision_chan.take()
            await _dispatch_debuglink_decision(msg)

    async def return_layout_change() -> None:
        content = await layout_change_chan.take()
        assert DEBUG_CONTEXT is not None
        if storage.layout_watcher is LAYOUT_WATCHER_LAYOUT:
            await DEBUG_CONTEXT.write(DebugLinkLayout(lines=content))
        else:
            from trezor.messages import DebugLinkState

            await DEBUG_CONTEXT.write(DebugLinkState(layout_lines=content))
        storage.layout_watcher = LAYOUT_WATCHER_NONE

    async def touch_hold(x: int, y: int, duration_ms: int) -> None:
        from trezor import io

        await loop.sleep(duration_ms)
        loop.synthetic_events.append((io.TOUCH, (io.TOUCH_END, x, y)))

    async def dispatch_DebugLinkWatchLayout(
        ctx: wire.Context, msg: DebugLinkWatchLayout
    ) -> Success:
        from trezor import ui

        layout_change_chan.putters.clear()
        if msg.watch:
            await ui.wait_until_layout_is_running()
        storage.watch_layout_changes = bool(msg.watch)
        log.debug(__name__, "Watch layout changes: %s", storage.watch_layout_changes)
        return Success()

    async def dispatch_DebugLinkDecision(
        ctx: wire.Context, msg: DebugLinkDecision
    ) -> None:
        from trezor import io

        if debuglink_decision_chan.putters:
            log.warning(__name__, "DebugLinkDecision queue is not empty")
        x = msg.x  # local_cache_attribute
        y = msg.y  # local_cache_attribute

        if x is not None and y is not None:
            evt_down = io.TOUCH_START, x, y
            evt_up = io.TOUCH_END, x, y
            loop.synthetic_events.append((io.TOUCH, evt_down))
            if msg.hold_ms is not None:
                loop.schedule(touch_hold(x, y, msg.hold_ms))
            else:
                loop.synthetic_events.append((io.TOUCH, evt_up))
        else:
            debuglink_decision_chan.publish(msg)

        if msg.wait:
            storage.layout_watcher = LAYOUT_WATCHER_LAYOUT
            loop.schedule(return_layout_change())

    async def dispatch_DebugLinkGetState(
        ctx: wire.Context, msg: DebugLinkGetState
    ) -> DebugLinkState | None:
        from trezor.messages import DebugLinkState
        from apps.common import mnemonic, passphrase

        m = DebugLinkState()
        m.mnemonic_secret = mnemonic.get_secret()
        m.mnemonic_type = mnemonic.get_type()
        m.passphrase_protection = passphrase.is_enabled()
        m.reset_entropy = storage.reset_internal_entropy

        if msg.wait_layout:
            if not storage.watch_layout_changes:
                raise wire.ProcessError("Layout is not watched")
            storage.layout_watcher = LAYOUT_WATCHER_STATE
            loop.schedule(return_layout_change())
            return None
        else:
            m.layout_lines = storage.current_content

        if msg.wait_word_pos:
            m.reset_word_pos = await reset_word_index.take()
        if msg.wait_word_list:
            m.reset_word = " ".join(await reset_current_words.take())
        return m

    async def dispatch_DebugLinkRecordScreen(
        ctx: wire.Context, msg: DebugLinkRecordScreen
    ) -> Success:
        if msg.target_directory:
            storage.save_screen_directory = msg.target_directory
            storage.save_screen = True
        else:
            storage.save_screen = False
            display.clear_save()  # clear C buffers

        return Success()

    async def dispatch_DebugLinkReseedRandom(
        ctx: wire.Context, msg: DebugLinkReseedRandom
    ) -> Success:
        if msg.value is not None:
            from trezor.crypto import random

            random.reseed(msg.value)
        return Success()

    async def dispatch_DebugLinkEraseSdCard(
        ctx: wire.Context, msg: DebugLinkEraseSdCard
    ) -> Success:
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

    def boot() -> None:
        register = workflow_handlers.register  # local_cache_attribute

        register(MessageType.DebugLinkDecision, dispatch_DebugLinkDecision)  # type: ignore [Argument of type "(ctx: Context, msg: DebugLinkDecision) -> Coroutine[Any, Any, None]" cannot be assigned to parameter "handler" of type "Handler[Msg@register]" in function "register"]
        register(MessageType.DebugLinkGetState, dispatch_DebugLinkGetState)  # type: ignore [Argument of type "(ctx: Context, msg: DebugLinkGetState) -> Coroutine[Any, Any, DebugLinkState | None]" cannot be assigned to parameter "handler" of type "Handler[Msg@register]" in function "register"]
        register(MessageType.DebugLinkReseedRandom, dispatch_DebugLinkReseedRandom)
        register(MessageType.DebugLinkRecordScreen, dispatch_DebugLinkRecordScreen)
        register(MessageType.DebugLinkEraseSdCard, dispatch_DebugLinkEraseSdCard)
        register(MessageType.DebugLinkWatchLayout, dispatch_DebugLinkWatchLayout)

        loop.schedule(debuglink_decision_dispatcher())
        if storage.layout_watcher is not LAYOUT_WATCHER_NONE:
            loop.schedule(return_layout_change())
