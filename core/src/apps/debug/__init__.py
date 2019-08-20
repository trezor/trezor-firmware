if not __debug__:
    from trezor.utils import halt

    halt("debug mode inactive")

if __debug__:
    from trezor import config, log, loop, utils
    from trezor.messages import MessageType
    from trezor.wire import register

    if False:
        from typing import Optional
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

    async def debuglink_decision_dispatcher():
        from trezor.ui import confirm, swipe

        while True:
            msg = await debuglink_decision_chan.take()

            if msg.yes_no is not None:
                await confirm_chan.put(
                    confirm.CONFIRMED if msg.yes_no else confirm.CANCELLED
                )
            if msg.up_down is not None:
                await swipe_chan.put(
                    swipe.SWIPE_DOWN if msg.up_down else swipe.SWIPE_UP
                )
            if msg.input is not None:
                await input_chan.put(msg.input)

    loop.schedule(debuglink_decision_dispatcher())

    async def dispatch_DebugLinkDecision(
        ctx: wire.Context, msg: DebugLinkDecision
    ) -> None:

        if debuglink_decision_chan.putters:
            log.warning(__name__, "DebugLinkDecision queue is not empty")

        debuglink_decision_chan.publish(msg)

    async def dispatch_DebugLinkGetState(
        ctx: wire.Context, msg: DebugLinkGetState
    ) -> DebugLinkState:
        from trezor.messages.DebugLinkState import DebugLinkState
        from apps.common import storage, mnemonic

        m = DebugLinkState()
        m.mnemonic_secret = mnemonic.get_secret()
        m.mnemonic_type = mnemonic.get_type()
        m.passphrase_protection = storage.device.has_passphrase()
        m.reset_entropy = reset_internal_entropy

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
