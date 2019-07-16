if not __debug__:
    from trezor.utils import halt

    halt("debug mode inactive")

if __debug__:
    from trezor import config, loop, utils
    from trezor.messages import MessageType
    from trezor.wire import register, protobuf_workflow

    if False:
        from typing import List, Optional
        from trezor import wire
        from trezor.messages.DebugLinkDecision import DebugLinkDecision
        from trezor.messages.DebugLinkGetState import DebugLinkGetState
        from trezor.messages.DebugLinkState import DebugLinkState

    reset_internal_entropy = None  # type: Optional[bytes]
    reset_current_words = None  # type: Optional[List[str]]
    reset_word_index = None  # type: Optional[int]

    confirm_signal = loop.signal()
    swipe_signal = loop.signal()
    input_signal = loop.signal()

    async def dispatch_DebugLinkDecision(
        ctx: wire.Context, msg: DebugLinkDecision
    ) -> None:
        from trezor.ui import confirm, swipe

        if msg.yes_no is not None:
            confirm_signal.send(confirm.CONFIRMED if msg.yes_no else confirm.CANCELLED)
        if msg.up_down is not None:
            swipe_signal.send(swipe.SWIPE_DOWN if msg.up_down else swipe.SWIPE_UP)
        if msg.input is not None:
            input_signal.send(msg.input)

    async def dispatch_DebugLinkGetState(
        ctx: wire.Context, msg: DebugLinkGetState
    ) -> DebugLinkState:
        from trezor.messages.DebugLinkState import DebugLinkState
        from apps.common import storage, mnemonic

        m = DebugLinkState()
        m.mnemonic_secret, m.mnemonic_type = mnemonic.get()
        m.passphrase_protection = storage.device.has_passphrase()
        m.reset_word_pos = reset_word_index
        m.reset_entropy = reset_internal_entropy
        if reset_current_words:
            m.reset_word = " ".join(reset_current_words)
        return m

    def boot() -> None:
        # wipe storage when debug build is used on real hardware
        if not utils.EMULATOR:
            config.wipe()

        register(
            MessageType.DebugLinkDecision, protobuf_workflow, dispatch_DebugLinkDecision
        )
        register(
            MessageType.DebugLinkGetState, protobuf_workflow, dispatch_DebugLinkGetState
        )
