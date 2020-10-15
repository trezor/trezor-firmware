if not __debug__:
    from trezor.utils import halt

    halt("debug mode inactive")

if __debug__:
    from trezor import io, ui, wire
    from trezor.messages import MessageType, DebugSwipeDirection
    from trezor.messages.DebugLinkLayout import DebugLinkLayout
    from trezor import config, crypto, log, loop, utils
    from trezor.messages.Success import Success

    if False:
        from typing import List, Optional
        from trezor.messages.DebugLinkDecision import DebugLinkDecision
        from trezor.messages.DebugLinkGetState import DebugLinkGetState
        from trezor.messages.DebugLinkRecordScreen import DebugLinkRecordScreen
        from trezor.messages.DebugLinkReseedRandom import DebugLinkReseedRandom
        from trezor.messages.DebugLinkState import DebugLinkState
        from trezor.messages.DebugLinkEraseSdCard import DebugLinkEraseSdCard
        from trezor.messages.DebugLinkWatchLayout import DebugLinkWatchLayout

    save_screen = False
    save_screen_directory = "."

    reset_internal_entropy: Optional[bytes] = None
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
    current_content: List[str] = []
    watch_layout_changes = False

    def screenshot() -> bool:
        if save_screen:
            ui.display.save(save_screen_directory + "/refresh-")
            return True
        return False

    def notify_layout_change(layout: ui.Layout) -> None:
        global current_content
        current_content = layout.read_content()
        if watch_layout_changes:
            layout_change_chan.publish(current_content)

    async def debuglink_decision_dispatcher() -> None:
        from trezor.ui.components.tt import confirm, swipe

        while True:
            msg = await debuglink_decision_chan.take()
            if msg.yes_no is not None:
                await confirm_chan.put(
                    ui.Result(confirm.CONFIRMED if msg.yes_no else confirm.CANCELLED)
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
                await input_chan.put(ui.Result(msg.input))

    loop.schedule(debuglink_decision_dispatcher())

    async def return_layout_change(ctx: wire.Context) -> None:
        content = await layout_change_chan.take()
        await ctx.write(DebugLinkLayout(lines=content))

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
        if debuglink_decision_chan.putters:
            log.warning(__name__, "DebugLinkDecision queue is not empty")

        if msg.x is not None:
            evt_down = io.TOUCH_START, msg.x, msg.y
            evt_up = io.TOUCH_END, msg.x, msg.y
            loop.synthetic_events.append((io.TOUCH, evt_down))
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
            ui.display.clear_save()  # clear C buffers

        return Success()

    async def dispatch_DebugLinkReseedRandom(
        ctx: wire.Context, msg: DebugLinkReseedRandom
    ) -> Success:
        if msg.value is not None:
            crypto.random.reseed(msg.value)
        return Success()

    async def dispatch_DebugLinkEraseSdCard(
        ctx: wire.Context, msg: DebugLinkEraseSdCard
    ) -> Success:
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

        wire.add(MessageType.LoadDevice, __name__, "load_device")
        wire.add(MessageType.DebugLinkShowText, __name__, "show_text")
        wire.register(MessageType.DebugLinkDecision, dispatch_DebugLinkDecision)  # type: ignore
        wire.register(MessageType.DebugLinkGetState, dispatch_DebugLinkGetState)
        wire.register(MessageType.DebugLinkReseedRandom, dispatch_DebugLinkReseedRandom)
        wire.register(MessageType.DebugLinkRecordScreen, dispatch_DebugLinkRecordScreen)
        wire.register(MessageType.DebugLinkEraseSdCard, dispatch_DebugLinkEraseSdCard)
        wire.register(MessageType.DebugLinkWatchLayout, dispatch_DebugLinkWatchLayout)
