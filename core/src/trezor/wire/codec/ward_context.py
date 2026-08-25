"""The WARD service endpoint on the V1 codec: one reader, and an inversion built out of a mailbox.

WHY THIS IS NOT `handle_session_codec`. The service interface is not a host-driven wallet
interface. Before binding it accepts one message and refuses everything else; after binding the
device is the sole initiator and nothing arriving there should ever reach the workflow dispatcher,
which would `workflow.spawn` and interrupt a signing flow the daemon has no business touching.

WHY IT IS ONE READER AND NOT A HANDOFF. THP inverts the channel by having the dispatcher let go
(`InterfaceContext.release_dispatch`), leaving the waiting workflow as the only reader. That has no
codec equivalent: `loop.wait` keeps every task paused on an interface in one set and `io.poll`
wakes ALL of them, so two readers on `iface_ward` would both call `iface.read()` and one would get
the other's bytes. So the reader never lets go. What changes when an RPC is in flight is where the
message it read goes: into the reply mailbox the workflow is parked on, instead of the bootstrap
handler.

The single-initiator rule is unchanged and still structural -- there is exactly one reader, and one
place that decides what to do with what it read.

WHAT THE TWO BUFFER SOURCES ARE FOR. An RPC reply can be large (a sync response carries a chain),
and it happens inside a wallet workflow, which is the moment at which borrowing the shared buffer
is safe -- the wallet request has been decoded and its response is not encoded yet. Unsolicited
traffic has no such guarantee, so it reads into a small private buffer that borrows nothing. A
daemon that sends something huge unsolicited gets the ordinary heap path and, failing that, the
ordinary refusal; what it cannot do is take the buffer a live wallet workflow is about to need.
"""

from typing import TYPE_CHECKING

from trezor import loop, protobuf
from trezor.wire import protocol_common
from trezor.wire.codec.codec_context import CodecContext
from trezor.wire.message_handler import decode_message, failure
from trezor.wire.protocol_common import Message

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from typing import Awaitable

    from storage.cache_common import DataCache
    from trezorio import WireInterface

    from .buffers import CodecBufferSource


class WardCodecContext(CodecContext):
    """Codec framing for the service interface, and nothing else.

    NO SESSION, DELIBERATELY. `wardd` must not create or activate a protocol-v1 wallet session, so
    this has no reachable `cache`: the seed-derived work stays in the wallet workflow that started
    the operation, and this end is only transport. Overriding rather than inheriting silently is
    the point -- `CodecContext.cache` would hand out `storage.cache_codec`'s active session, which
    is the wallet's.
    """

    def __init__(
        self,
        iface: WireInterface,
        bootstrap: CodecBufferSource,
        pooled: CodecBufferSource,
    ) -> None:
        super().__init__(iface, bootstrap)
        # WHAT `apps.ward.service` READS FROM A LINK. Its `ServiceLink` union logs and tears down
        # through `channel_id` and `iface` on either transport, so this end has to carry both --
        # and `Context` declares `channel_id` without defining it, so inheriting is not enough.
        # Zero because there are no channels here to tell apart, not because this is channel zero.
        self.channel_id = 0
        self._bootstrap = bootstrap
        self._pooled = pooled
        # Read by the reader loop to decide where a message goes, and by `_select_buffers` to
        # decide which memory it lands in. Both questions have the same answer, which is why there
        # is one flag rather than two.
        self.rpc_in_flight = False
        self.reply: loop.mailbox[Message | BaseException] = loop.mailbox()

    def _select_buffers(self) -> None:
        self.buffers = self._pooled if self.rpc_in_flight else self._bootstrap

    def read_from_wire(self) -> Awaitable[Message]:
        self._select_buffers()
        return super().read_from_wire()

    async def write(self, msg: protobuf.MessageType) -> None:
        self._select_buffers()
        await super().write(msg)

    def release(self) -> None:
        pass

    @property
    def cache(self) -> DataCache:
        raise RuntimeError("the WARD service endpoint has no session")


_CONTEXT: WardCodecContext | None = None


def service_link() -> WardCodecContext:
    """The endpoint, or a `DataError` if this build is not serving one.

    Not an assertion: the loop is torn down and rebuilt on every MicroPython session restart, so
    "there is no endpoint right now" is a state a WARD operation can genuinely meet, and it has to
    fail the operation rather than the firmware.
    """
    from trezor.wire import DataError

    if _CONTEXT is None:
        raise DataError("the WARD service interface is not being served")
    return _CONTEXT


def _drop_pending(ctx: WardCodecContext) -> None:
    """Discard whatever is sitting in the mailbox, giving its receive lease back.

    Reachable whenever an RPC gave up before its answer arrived: the reader had already read it
    and put it somewhere nobody was waiting. A stale answer must never be handed to the NEXT
    request as if it were its own.
    """
    if ctx.reply.is_empty():
        return
    stale = ctx.reply.value
    ctx.reply.clear()
    if isinstance(stale, Message):
        stale.release()


async def exchange(request: protobuf.MessageType) -> Message:
    """Ask the daemon one question and return its raw answer.

    The deadline is the caller's: `apps.ward.service._rpc` bounds the whole exchange, including
    this write, because a write to an interface nobody is draining parks just as thoroughly as a
    read from a silent one.
    """
    from trezor.wire import DataError

    ctx = service_link()
    if ctx.rpc_in_flight:
        # One stream, no request ids: a second question in flight would make the two answers
        # indistinguishable. Cannot happen with one workflow at a time, and is a hard error rather
        # than a queue because queueing would be inventing a protocol.
        raise DataError("a WARD service RPC is already in flight")

    _drop_pending(ctx)
    ctx.rpc_in_flight = True
    try:
        await ctx.write(request)
        answer = await ctx.reply
        if isinstance(answer, BaseException):
            raise answer
        return answer
    finally:
        # CLEARED EVEN WHEN THE CALLER IS CLOSED under its deadline -- otherwise the reader would
        # keep routing into a mailbox nobody reads and the interface would never bootstrap again.
        ctx.rpc_in_flight = False


def tear_down(reason: str) -> None:
    """Give up on the conversation. The reader keeps reading.

    THIS IS WHERE CODEC IS BETTER OFF THAN THP. There is no channel to close, so a daemon that
    restarts simply announces itself again and is heard -- the lock-out that
    `InterfaceContext._retire_displaced_channel` exists to prevent cannot arise here.
    """
    if _CONTEXT is None:
        return
    if __debug__:
        log.error(
            __name__,
            "giving up on the service conversation: %s",
            reason,
            iface=_CONTEXT.iface,
        )
    _CONTEXT.rpc_in_flight = False
    _drop_pending(_CONTEXT)
    _CONTEXT.buffers = _CONTEXT._bootstrap


async def _handle_bootstrap(ctx: WardCodecContext, msg: Message) -> None:
    """The one message an unbound service interface accepts, and the refusal for everything else.

    SHAPE ONLY, NOT POLICY -- the same split as `thp/received_message_handler`. Whether this daemon
    may bind is the handler's business; whether this is a message the interface will look at at all
    is decided here, before any dispatcher or workflow sees it.
    """
    from trezor.enums import MessageType
    from trezor.wire import DataError

    if msg.type != MessageType.WardServiceOpen:
        msg.release()
        await ctx.write(failure(DataError("not accepted on the WARD service channel")))
        return

    from trezor.messages import WardServiceOpen

    from apps.ward.service import bind_codec

    try:
        # NOT `handle_single_message`, and not `find_handler`. The first would `workflow.spawn`
        # and close a live wallet workflow, which a daemon announcing itself has no business
        # doing; the second would make every registered message reachable here.
        response = await bind_codec(decode_message(msg, WardServiceOpen), ctx.iface)
    except Exception as exc:
        if __debug__:
            log.exception(__name__, exc, iface=ctx.iface)
        response = failure(exc)

    await ctx.write(response)


async def handle_ward_codec_interface(
    iface: WireInterface,
    bootstrap: CodecBufferSource,
    pooled: CodecBufferSource,
) -> None:
    """The single reader of the WARD service interface.

    Modelled on the DebugLink loop (`apps.debug.handle_session`), which is the precedent in this
    tree for a second codec interface with its own buffer that never restarts the machine. It
    must not `loop.clear()`: doing so from here would tear down the wallet session on the strength
    of something a daemon said.
    """
    global _CONTEXT

    ctx = _CONTEXT = WardCodecContext(iface, bootstrap, pooled)
    if __debug__:
        log.debug(__name__, "serving the service interface", iface=iface)

    try:
        while True:
            try:
                msg = await ctx.read_from_wire()
            except protocol_common.WireError as exc:
                if __debug__:
                    log.exception(__name__, exc, iface=iface)
                if ctx.rpc_in_flight:
                    # FAIL THE OPERATION, DO NOT ANSWER. The device is the initiator here, so a
                    # `Failure` would be a reply to a request nobody made. `mailbox` raises a
                    # value that is an exception, so the workflow learns immediately rather than
                    # sitting out its full deadline.
                    ctx.reply.put(exc, replace=True)
                else:
                    await ctx.write(failure(exc))
                continue

            if ctx.rpc_in_flight:
                _drop_pending(ctx)
                ctx.reply.put(msg)
                continue

            await _handle_bootstrap(ctx, msg)
    finally:
        if __debug__:
            log.debug(__name__, "stopped serving the service interface", iface=iface)
        _CONTEXT = None
