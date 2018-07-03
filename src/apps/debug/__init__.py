if not __debug__:
    from trezor.utils import halt

    halt("debug mode inactive")

if __debug__:
    from trezor import loop
    from trezor.messages import MessageType
    from trezor.messages.DebugLinkState import DebugLinkState
    from trezor.ui import confirm, swipe
    from trezor.wire import register, protobuf_workflow
    from apps.common import storage

    reset_internal_entropy = None
    reset_current_words = None
    reset_word_index = None

    confirm_signal = loop.signal()
    swipe_signal = loop.signal()
    input_signal = loop.signal()

    async def dispatch_DebugLinkDecision(ctx, msg):
        if msg.yes_no is not None:
            confirm_signal.send(confirm.CONFIRMED if msg.yes_no else confirm.CANCELLED)
        if msg.up_down is not None:
            swipe_signal.send(swipe.SWIPE_DOWN if msg.up_down else swipe.SWIPE_UP)
        if msg.input is not None:
            input_signal.send(msg.input)

    async def dispatch_DebugLinkGetState(ctx, msg):
        m = DebugLinkState()
        m.mnemonic = storage.get_mnemonic()
        m.passphrase_protection = storage.has_passphrase()
        m.reset_word_pos = reset_word_index
        m.reset_entropy = reset_internal_entropy
        if reset_current_words:
            m.reset_word = " ".join(reset_current_words)
        return m

    def boot():
        # wipe storage when debug build is used
        storage.wipe()

        register(
            MessageType.DebugLinkDecision, protobuf_workflow, dispatch_DebugLinkDecision
        )
        register(
            MessageType.DebugLinkGetState, protobuf_workflow, dispatch_DebugLinkGetState
        )
