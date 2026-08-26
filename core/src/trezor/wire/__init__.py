"""
# Wire

Handles on-the-wire communication with a host computer. The communication is:

- Request / response.
- Protobuf-encoded, see `protobuf.py`.
- Wrapped in a simple envelope format, see `trezor/wire/codec/codec_v1.py` or `trezor/wire/thp/context.py`.
- Transferred over USB interface, or UDP in case of Unix emulation.

This module:

1. Runs workflows, also called `handlers`, to process the message.
2. Creates and passes the `Context` object to the handlers. This provides an interface to
   wait, read, write etc. on the wire.

## Session handler

When the `wire.setup` is called the `handle_session` coroutine is scheduled. The
`handle_session` waits for some messages to be received on some particular interface and
reads the message's header. When the message type is known the first handler is called. This way the
`handle_session` goes through all the workflows.

"""

from typing import TYPE_CHECKING

from trezor import loop, protobuf, utils

from .. import workflow
from . import message_handler, protocol_common

if utils.USE_THP:
    from .thp import received_message_handler
    from .thp.interface_context import ThpContext
else:
    from .codec.codec_context import CodecContext

from .context import UnexpectedMessageException
from .message_handler import failure

# Import all errors into namespace, so that `wire.Error` is available from
# other packages.
from .errors import *  # isort:skip # noqa: F401,F403

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from trezorio import WireInterface
    from types import TracebackType
    from typing import Any, Callable, Coroutine, Generic, Type, TypeVar

    from trezor.wire.thp.channel import Channel
    from trezor.wire.thp.interface_context import InterfaceContext

    T = TypeVar("T")
    Msg = TypeVar("Msg", bound=protobuf.MessageType)
    HandlerTask = Coroutine[Any, Any, protobuf.MessageType]
    Handler = Callable[[Msg], HandlerTask]

    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)
else:
    Generic = (object,)
    T = 0


class _HighSpeed:
    def __enter__(self) -> "_HighSpeed":
        if utils.USE_BLE:
            from trezorble import set_high_speed

            set_high_speed(True)
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if utils.USE_BLE:
            from trezorble import set_high_speed

            set_high_speed(False)
        return False


high_speed: "_HighSpeed" = _HighSpeed()


class Provider(Generic[T]):
    def __init__(self, obj: T) -> None:
        self.obj = obj

    def take(self) -> T | None:
        if self.obj is None:
            return None

        obj = self.obj
        self.obj = None
        return obj


from .buffers import PROTOBUF_BUFFER_SIZE, SharedBuffer, WireBuffer

if utils.USE_WARD_SERVICE_CHANNEL:
    # A PRIVATE BUFFER FOR UNSOLICITED TRAFFIC. Only `WardServiceOpen` is accepted while no RPC
    # is in flight, and it is tiny; what this size really buys is that a daemon cannot take the
    # shared buffer at a moment when a wallet workflow is about to need it.
    _WARD_BOOTSTRAP_BUFFER_SIZE = 512

    # Big enough for the requests the device sends -- a fetch, a sync, a publish header -- so the
    # shared buffer is reached for by a large chain response and by nothing else.
    _WARD_RPC_SMALL_BUFFER_SIZE = 256

    # AND HARD CEILINGS, WHICH ARE NOT THE SAME AS BUFFER SIZES. Above `capacity()` the codec has
    # always fallen back to the heap, so without these an unauthenticated endpoint could turn an
    # advertised uint32 into an allocation attempt. `PROTOBUF_BUFFER_SIZE` is the real protocol
    # bound -- what a chain fold has to fit in.
    _WARD_BOOTSTRAP_MAX_MESSAGE = _WARD_BOOTSTRAP_BUFFER_SIZE
    _WARD_RPC_MAX_MESSAGE = PROTOBUF_BUFFER_SIZE

    def _schedule_ward_codec_endpoint(
        iface: WireInterface, shared: SharedBuffer
    ) -> None:
        """The WARD service endpoint, on EITHER kind of build.

        THE SERVICE INTERFACE SPEAKS CODEC V1 EVEN WHEN THE WALLET INTERFACE SPEAKS THP. WARD's
        own cryptography is what makes a WARD state trustworthy -- leaf sealing, the trie proof,
        the WM-attested head -- so a transport that authenticates the daemon buys no property the
        protocol does not already have, while a THP service channel costs a private dispatcher,
        channel reattachment, replacement semantics, a persistent daemon pin, and a channel table
        shared with the wallet interface. All of that is kept behind `USE_WARD_SERVICE_THP` rather
        than deleted; none of it is built by default.

        The `shared` buffer is the build's own large one, so the endpoint CONTENDS with wallet
        traffic rather than duplicating 8.5 kB. That is the intended model and what the
        per-message leasing exists for: it is a distinct `BufferSource`, so it is refused while
        the wallet holds the lease rather than handed memory the wallet is using.
        """
        from .codec.buffers import CodecBufferSource, private_source
        from .codec.ward_context import handle_ward_codec_interface

        loop.schedule(
            handle_ward_codec_interface(
                iface,
                private_source(
                    _WARD_BOOTSTRAP_BUFFER_SIZE, _WARD_BOOTSTRAP_MAX_MESSAGE
                ),
                CodecBufferSource(
                    WireBuffer(_WARD_RPC_SMALL_BUFFER_SIZE),
                    shared,
                    _WARD_RPC_MAX_MESSAGE,
                ),
            )
        )


if utils.USE_THP:
    from .buffers import SMALL_BUFFER_SIZE, BufferSource

    # Allocate THP read/write buffers in more stable area of memory
    #
    # THE LARGE BUFFERS ARE SHARED BY EVERY CHANNEL and borrowed for the length of one message.
    # What a channel needs for its whole life is small; 8.5 kB is needed only while a large message
    # is actually in flight. Separate receive and send buffers, so a large message arriving on one
    # interface does not block a large one being sent on another -- the two directions never
    # contend with each other, only same-direction traffic on two channels does.
    _SHARED_RECEIVE_BUFFER = SharedBuffer()
    _SHARED_SEND_BUFFER = SharedBuffer()

    def _buffer_sources() -> "tuple[BufferSource, BufferSource]":
        """A (receive, send) pair: small buffers of its own, the large ones borrowed."""
        return (
            BufferSource(WireBuffer(SMALL_BUFFER_SIZE), _SHARED_RECEIVE_BUFFER),
            BufferSource(WireBuffer(SMALL_BUFFER_SIZE), _SHARED_SEND_BUFFER),
        )

    THP_BUFFERS_PROVIDER = Provider(_buffer_sources())

    if utils.USE_WARD_SERVICE_THP:
        # A POOL OF ITS OWN, so the WARD service interface can hold a channel while a wallet
        # channel is live on another interface -- which is the entire point of giving the service
        # its own interface. What that costs is now a second SMALL pair rather than a second large
        # one: the interfaces share the large buffers and take turns per message, which is what the
        # WARD flow does anyway (the wallet request is decoded before the RPC begins and the wallet
        # response encoded after it ends).
        WARD_BUFFERS_PROVIDER = Provider(_buffer_sources())

    def is_ward_interface(iface: WireInterface) -> bool:
        """Whether this is the interface the WARD service is served on.

        One predicate rather than a check repeated at each site, because "which interface is this?"
        is asked for several unrelated reasons -- which buffer pool it draws from, and whether a
        channel replacement on it should behave like a wallet host reconnecting.
        """
        if not utils.USE_WARD_SERVICE_CHANNEL:
            return False

        import usb

        return iface is usb.iface_ward

    def buffers_provider_for(iface: WireInterface) -> Provider:
        """Which pool this interface draws its channel buffers from.

        ONE PROVIDER MEANS ONE CHANNEL AT A TIME, because a provider hands out its pair once and
        then answers None. USB and BLE deliberately share `THP_BUFFERS_PROVIDER`: a session serves
        one channel, and an interface that cannot get buffers answers TRANSPORT_BUSY, which is how
        a second host is turned away.

        That is exactly the sharing an interface hosting a service channel must not do -- it has to
        be able to hold a channel WHILE another interface holds one -- so such an interface gets a
        pool of its own. Decided here, per interface, rather than by position: "the second
        interface to receive a packet" would hand a private pool to whichever of USB or BLE
        happened to be second, silently changing how a second host is refused today.
        """
        if utils.USE_WARD_SERVICE_THP and is_ward_interface(iface):
            return WARD_BUFFERS_PROVIDER

        return THP_BUFFERS_PROVIDER

    if __debug__:
        _THP_IFACES: list[InterfaceContext] = []

        def find_thp_channel(channel_id: AnyBytes) -> Channel | None:
            """Used by `DebugLinkGetPairingInfo` (only for tests). Currently only
            works with channels that have active workflow (e.g. pairing)."""
            for ifctx in _THP_IFACES:
                if (
                    ifctx.active_channel
                    and ifctx.active_channel.channel_id_bytes() == channel_id
                ):
                    return ifctx.active_channel
            return None

    def setup(*ifaces: WireInterface) -> None:
        """Initialize the wire stack on the provided interfaces.

        The WARD service interface is served by its own codec-v1 reader and is NOT handed to the
        THP stack -- see `_schedule_ward_codec_endpoint`. It is therefore absent from
        `ThpContext`, which is what keeps service traffic out of the THP channel tables, the
        dispatch channel and the retransmission scheduler entirely, rather than out of them by
        agreement.
        """
        thp_ifaces = []
        for iface in ifaces:
            if utils.USE_WARD_SERVICE_CHANNEL and is_ward_interface(iface):
                if not utils.USE_WARD_SERVICE_THP:
                    _schedule_ward_codec_endpoint(iface, _SHARED_RECEIVE_BUFFER)
                    continue
            thp_ifaces.append(iface)
        loop.schedule(handle_session_thp(*thp_ifaces))

    async def handle_session_thp(*ifaces: WireInterface) -> None:
        ctx = ThpContext(*ifaces)
        if __debug__:
            _THP_IFACES[:] = ctx._iface_ctxs

        try:
            # wait until channel activity (on any interface)
            channel = await ctx.get_dispatch_channel()

            # at this point channel has valid message waiting
            # process messages until it returns do_not_restart=False
            while await received_message_handler.handle_received_message(channel):
                if __debug__:
                    log.debug(
                        __name__,
                        "Skipping THP session restart on channel %04x",
                        channel.channel_id,
                        iface=channel.iface,
                    )

        finally:
            if __debug__:
                log.debug(__name__, "Finished THP session: %s", ifaces)
            # Wait for all active workflows to finish.
            await workflow.join_all()
            if __debug__:
                import apps.debug

                await apps.debug.close_session()
            # Send out any queued messages.
            await ctx.close()
            loop.clear()

else:

    from .codec.buffers import CodecBufferSource

    # THE LARGE BUFFER IS BORROWED, NOT OWNED. It used to be handed to the first interface that
    # read a valid header and never given back, which is fine while one interface is ever reading
    # -- and impossible once the WARD service interface has to talk to the daemon in the middle of
    # a wallet workflow. Now every interface has a small buffer of its own and takes a lease on
    # this one for the length of a single message.
    #
    # Reallocated once per session, as before. Now `PROTOBUF_BUFFER_SIZE` rather than the V1
    # codec's historical 8192: the two transports share `SharedBuffer`/`BufferSource` and the
    # WARD chain fold is capped by whichever of them a build happens to have, so two sizes meant
    # the same protocol bound differed by transport for no reason anyone could state.
    _WIRE_BUFFER_SIZE = PROTOBUF_BUFFER_SIZE
    _SHARED_WIRE_BUFFER = SharedBuffer(_WIRE_BUFFER_SIZE)

    # Big enough for the wallet traffic a device sends and receives by the thousand -- Features,
    # Success, PublicKey, Address, the signing exchanges -- so the shared buffer is reached for by
    # the rare large message and by nothing else.
    _WALLET_SMALL_BUFFER_SIZE = 256

    def _codec_buffers(small_size: int = _WALLET_SMALL_BUFFER_SIZE) -> CodecBufferSource:
        return CodecBufferSource(WireBuffer(small_size), _SHARED_WIRE_BUFFER)

    def is_ward_interface(iface: WireInterface) -> bool:
        """Whether this is the interface the WARD service is served on."""
        if not utils.USE_WARD_SERVICE_CHANNEL:
            return False

        import usb

        return iface is usb.iface_ward

    def setup(*ifaces: WireInterface) -> None:
        """Initialize the wire stack on the provided interfaces."""
        for iface in ifaces:
            if utils.USE_WARD_SERVICE_CHANNEL and is_ward_interface(iface):
                # NOT `handle_session_codec`: the service interface is device-initiated after
                # binding and must never reach the workflow dispatcher. See
                # `trezor.wire.codec.ward_context`.
                _schedule_ward_codec_endpoint(iface, _SHARED_WIRE_BUFFER)
            else:
                loop.schedule(handle_session_codec(iface))

    async def handle_session_codec(iface: WireInterface) -> None:
        ctx = CodecContext(iface, _codec_buffers())
        next_msg: protocol_common.Message | None = None

        # Take a mark of modules that are imported at this point, so we can
        # roll back and un-import any others.
        modules = utils.unimport_begin()
        while True:
            try:
                if next_msg is None:
                    # If the previous run did not keep an unprocessed message for us,
                    # wait for a new one coming from the wire.
                    try:
                        msg = await ctx.read_from_wire()
                    except protocol_common.WireError as exc:
                        if __debug__:
                            log.exception(__name__, exc, iface=iface)
                        await ctx.write(failure(exc))
                        continue
                else:
                    # Process the message from previous run.
                    msg = next_msg
                    next_msg = None

                do_not_restart = False
                try:
                    do_not_restart = await message_handler.handle_single_message(
                        ctx, msg
                    )
                except UnexpectedMessageException as unexpected:
                    # The workflow was interrupted by an unexpected message. We need to
                    # process it as if it was a new message...
                    next_msg = unexpected.msg
                    # ...and we must not restart because that would lose the message.
                    do_not_restart = True
                    continue
                except Exception as exc:
                    # Log and ignore. The session handler can only exit explicitly in the
                    # following finally block.
                    if __debug__:
                        log.exception(__name__, exc, iface=iface)
                finally:
                    # Unload modules imported by the workflow. Should not raise.
                    utils.unimport_end(modules)

                    if not do_not_restart:
                        # Wait for all active workflows to finish.
                        await workflow.join_all()
                        if __debug__:
                            import apps.debug

                            await apps.debug.close_session()
                        # Let the session be restarted from `main`.
                        loop.clear()
                        return  # pylint: disable=lost-exception

            except Exception as exc:
                # Log and try again. The session handler can only exit explicitly via
                # loop.clear() above.
                if __debug__:
                    log.exception(__name__, exc, iface=iface)
