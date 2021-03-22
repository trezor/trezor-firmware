if not __debug__:
    from trezor.utils import halt

    halt("debug mode inactive")

if __debug__:
    from trezor import config, log, loop, utils, wire
    from trezor.ui import display
    from trezor.messages import MessageType
    from trezor.messages.DebugLinkLayout import DebugLinkLayout
    from trezor.messages.Success import Success

    from apps import workflow_handlers

    if False:
        from trezor.ui import Layout
        from trezor.messages.DebugLinkDecision import DebugLinkDecision
        from trezor.messages.DebugLinkGetState import DebugLinkGetState
        from trezor.messages.DebugLinkLayout import DebugLinkLayout
        from trezor.messages.DebugLinkRecordScreen import DebugLinkRecordScreen
        from trezor.messages.DebugLinkReseedRandom import DebugLinkReseedRandom
        from trezor.messages.DebugLinkState import DebugLinkState
        from trezor.messages.DebugLinkEraseSdCard import DebugLinkEraseSdCard
        from trezor.messages.DebugLinkWatchLayout import DebugLinkWatchLayout

    save_screen = False
    save_screen_directory = "."

    reset_internal_entropy: bytes | None = None
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
    current_content: list[str] = []
    watch_layout_changes = False

    def screenshot() -> bool:
        if save_screen:
            display.save(save_screen_directory + "/refresh-")
            return True
        return False

    def notify_layout_change(layout: Layout) -> None:
        global current_content
        current_content = layout.read_content()
        if watch_layout_changes:
            layout_change_chan.publish(current_content)

    async def dispatch_debuglink_decision(msg: DebugLinkDecision) -> None:
        from trezor.messages import DebugSwipeDirection
        from trezor.ui import Result
        from trezor.ui.components.tt import confirm, swipe

        if msg.yes_no is not None:
            await confirm_chan.put(
                Result(confirm.CONFIRMED if msg.yes_no else confirm.CANCELLED)
            )
        if msg.swipe is not None:
            if msg.swipe == DebugSwipeDirection.UP:
                await swipe_chan.put(swipe.SWIPE_UP)
            elif msg.swipe == DebugSwipeDirection.DOWN:
                await swipe_chan.put(swipe.SWIPE_DOWN)
            elif msg.swipe == DebugSwipeDirection.LEFT:
                await swipe_chan.put(swipe.SWIPE_LEFT)
            elif msg.swipe == DebugSwipeDirection.RIGHT:
                await swipe_chan.put(swipe.SWIPE_RIGHT)
        if msg.input is not None:
            await input_chan.put(Result(msg.input))

    async def debuglink_decision_dispatcher() -> None:
        while True:
            msg = await debuglink_decision_chan.take()
            await dispatch_debuglink_decision(msg)

    loop.schedule(debuglink_decision_dispatcher())

    async def return_layout_change(ctx: wire.Context) -> None:
        content = await layout_change_chan.take()
        await ctx.write(DebugLinkLayout(lines=content))

    async def touch_hold(x: int, y: int, duration_ms: int) -> None:
        from trezor import io

        await loop.sleep(duration_ms)
        loop.synthetic_events.append((io.TOUCH, (io.TOUCH_END, x, y)))

    async def dispatch_DebugLinkWatchLayout(
        ctx: wire.Context, msg: DebugLinkWatchLayout
    ) -> Success:
        global watch_layout_changes
        layout_change_chan.putters.clear()
        watch_layout_changes = bool(msg.watch)
        log.debug(__name__, "Watch layout changes: {}".format(watch_layout_changes))
        return Success()

    async def dispatch_DebugLinkDecision(
        ctx: wire.Context, msg: DebugLinkDecision
    ) -> None:
        from trezor import io

        if debuglink_decision_chan.putters:
            log.warning(__name__, "DebugLinkDecision queue is not empty")

        if msg.x is not None and msg.y is not None:
            evt_down = io.TOUCH_START, msg.x, msg.y
            evt_up = io.TOUCH_END, msg.x, msg.y
            loop.synthetic_events.append((io.TOUCH, evt_down))
            if msg.hold_ms is not None:
                loop.schedule(touch_hold(msg.x, msg.y, msg.hold_ms))
            else:
                loop.synthetic_events.append((io.TOUCH, evt_up))
        else:
            debuglink_decision_chan.publish(msg)

        if msg.wait:
            loop.schedule(return_layout_change(ctx))

    async def dispatch_DebugLinkGetState(
        ctx: wire.Context, msg: DebugLinkGetState
    ) -> DebugLinkState:
        from trezor.messages.DebugLinkState import DebugLinkState
        from apps.common import mnemonic, passphrase

        m = DebugLinkState()
        m.mnemonic_secret = mnemonic.get_secret()
        m.mnemonic_type = mnemonic.get_type()
        m.passphrase_protection = passphrase.is_enabled()
        m.reset_entropy = reset_internal_entropy

        if msg.wait_layout:
            if not watch_layout_changes:
                raise wire.ProcessError("Layout is not watched")
            m.layout_lines = await layout_change_chan.take()
        else:
            m.layout_lines = current_content

        if msg.wait_word_pos:
            m.reset_word_pos = await reset_word_index.take()
        if msg.wait_word_list:
            m.reset_word = " ".join(await reset_current_words.take())
        return m

    async def dispatch_DebugLinkRecordScreen(
        ctx: wire.Context, msg: DebugLinkRecordScreen
    ) -> Success:
        global save_screen_directory
        global save_screen

        if msg.target_directory:
            save_screen_directory = msg.target_directory
            save_screen = True
        else:
            save_screen = False
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

        try:
            io.sdcard.power_on()
            if msg.format:
                io.fatfs.mkfs()
            else:
                # trash first 1 MB of data to destroy the FAT filesystem
                assert io.sdcard.capacity() >= 1024 * 1024
                empty_block = bytes([0xFF] * io.sdcard.BLOCK_SIZE)
                for i in range(1024 * 1024 // io.sdcard.BLOCK_SIZE):
                    io.sdcard.write(i, empty_block)

        except OSError:
            raise wire.ProcessError("SD card operation failed")
        finally:
            io.sdcard.power_off()
        return Success()

    def boot() -> None:
        # wipe storage when debug build is used on real hardware
        if not utils.EMULATOR:
            config.wipe()

        workflow_handlers.register(MessageType.DebugLinkDecision, dispatch_DebugLinkDecision)  # type: ignore
        workflow_handlers.register(
            MessageType.DebugLinkGetState, dispatch_DebugLinkGetState
        )
        workflow_handlers.register(
            MessageType.DebugLinkReseedRandom, dispatch_DebugLinkReseedRandom
        )
        workflow_handlers.register(
            MessageType.DebugLinkRecordScreen, dispatch_DebugLinkRecordScreen
        )
        workflow_handlers.register(
            MessageType.DebugLinkEraseSdCard, dispatch_DebugLinkEraseSdCard
        )
        workflow_handlers.register(
            MessageType.DebugLinkWatchLayout, dispatch_DebugLinkWatchLayout
        )
