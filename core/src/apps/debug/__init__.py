if not __debug__:
    from trezor.utils import halt

    halt("debug mode inactive")

if __debug__:
    from trezor import config, io, log, loop, ui, utils
    from trezor.messages import MessageType, DebugSwipeDirection
    from trezor.messages.DebugLinkLayout import DebugLinkLayout
    from trezor.wire import register

    if False:
        from typing import List, Optional
        from trezor import wire
        from trezor.messages.DebugLinkDecision import DebugLinkDecision
        from trezor.messages.DebugLinkGetState import DebugLinkGetState
        from trezor.messages.DebugLinkState import DebugLinkState

    reset_internal_entropy = None  # type: Optional[bytes]
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
    current_content = None  # type: Optional[List[str]]

    def notify_layout_change(layout: ui.Layout) -> None:
        global current_content
        current_content = layout.read_content()
        if layout_change_chan.takers:
            layout_change_chan.publish(current_content)

    async def debuglink_decision_dispatcher() -> None:
        from trezor.ui import confirm, swipe

        while True:
            msg = await debuglink_decision_chan.take()
            if msg.yes_no is not None:
                await confirm_chan.put(
                    confirm.CONFIRMED if msg.yes_no else confirm.CANCELLED
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
                await input_chan.put(msg.input)

    loop.schedule(debuglink_decision_dispatcher())

    async def return_layout_change(ctx: wire.Context) -> None:
        content = await layout_change_chan.take()
        await ctx.write(DebugLinkLayout(lines=content))

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
        from apps.common import mnemonic
        from apps.common.storage.device import has_passphrase

        m = DebugLinkState()
        m.mnemonic_secret = mnemonic.get_secret()
        m.mnemonic_type = mnemonic.get_type()
        m.passphrase_protection = has_passphrase()
        m.reset_entropy = reset_internal_entropy

        if msg.wait_layout or current_content is None:
            m.layout_lines = await layout_change_chan.take()
        else:
            m.layout_lines = current_content

        if msg.wait_word_pos:
            m.reset_word_pos = await reset_word_index.take()
        if msg.wait_word_list:
            m.reset_word = " ".join(await reset_current_words.take())
        return m

    def boot() -> None:
        # wipe storage when debug build is used on real hardware
        if not utils.EMULATOR:
            config.wipe()

        register(MessageType.DebugLinkDecision, dispatch_DebugLinkDecision)
        register(MessageType.DebugLinkGetState, dispatch_DebugLinkGetState)
