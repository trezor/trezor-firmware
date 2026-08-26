"""Where a codec-v1 message in flight gets its memory.

WHY THE CODEC NEEDED THIS AT ALL. The V1 codec had one 8 kB buffer behind a `Provider`, taken by
the first interface to read a valid header and never given back -- `Provider` has `take()` and no
counterpart. That is fine while one interface is ever reading, which is every codec build today,
and impossible the moment a WARD service interface has to talk to the daemon in the middle of a
wallet workflow: it cannot borrow what is never released.

So the codec now uses the same two tiers as THP (`trezor.wire.buffers`), with the lease ending at
the end of each message. What sits on top of them here is the V1 codec's own answer to a message
too large for the pool, which predates the pool and must not be lost: the heap, and if even that
fails, drain the message off the wire and refuse it. Those two tiers carry no lease, because there
is nothing shared to give back.
"""

from micropython import const
from typing import TYPE_CHECKING

from trezor.wire.buffers import BufferSource, SharedBuffer, WireBuffer

if TYPE_CHECKING:
    from buffer_types import AnyBuffer

# NO BOUND, spelled as the largest number the framing can carry. `msize` is a uint32 on the wire
# (`codec_v1._REP_INIT`), so a source that returns this refuses nothing on size alone -- which is
# what every host-driven wallet interface has always done and must keep doing.
UNBOUNDED_MESSAGE_SIZE = const(0xFFFF_FFFF)


class CodecBufferSource:
    """The pooled tiers for one codec connection: a small buffer of its own, a large one borrowed.

    `shared` is optional, and that is not a convenience: DebugLink runs its own interface with a
    private buffer precisely so it can never contend with wallet traffic, and a debug session that
    could be told "another session is in progress" would be one that stops working exactly when it
    is most needed.
    """

    def __init__(
        self,
        small: WireBuffer,
        shared: SharedBuffer | None = None,
        max_size: int | None = None,
    ) -> None:
        self._small = small
        self._shared = shared
        self._source = BufferSource(small, shared) if shared is not None else None
        self._max_size = UNBOUNDED_MESSAGE_SIZE if max_size is None else max_size

    def capacity(self) -> int:
        """The largest message this can serve. Above it the caller is on its own -- see the module
        docstring: that path is older than the pool and is deliberately still there."""
        if self._shared is None:
            return len(self._small.buf)
        return len(self._shared.buf)

    def max_message_size(self) -> int:
        """The largest message this source will take off the wire at all.

        DISTINCT FROM `capacity()`, which is only the largest one the POOL can serve: above
        capacity the codec has always fallen back to the heap, and for a wallet interface it still
        does. This is the harder limit above which a message is drained and refused without
        allocating anything, and the base source deliberately does not impose one -- the interface
        that needs it is the permanently listening, unauthenticated service endpoint, which
        overrides this.
        """
        return self._max_size

    def get(self, length: int) -> "AnyBuffer | None":
        """A buffer of `length`, or None if the shared one is held by someone else.

        Only valid for `length <= capacity()`. None is the codec's long-standing "another session
        in progress" -- what changes is that it is now decided per message rather than per session,
        so the loser is refused for as long as the other message is in flight and not a moment
        longer.
        """
        if self._source is None:
            return self._small.get(length)
        return self._source.try_get(length)

    def holds_shared(self) -> bool:
        """Whether a lease on the shared buffer is currently held by this source."""
        return self._source is not None and self._source.holds_shared()

    def release(self) -> None:
        """Done with the message; give the shared buffer back. Idempotent."""
        if self._source is not None:
            self._source.release()


def private_source(size: int, max_size: int | None = None) -> CodecBufferSource:
    """A source that borrows nothing, for an interface that must never contend."""
    return CodecBufferSource(WireBuffer(size), max_size=max_size)
