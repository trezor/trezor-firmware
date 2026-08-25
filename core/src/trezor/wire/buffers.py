"""The memory a wire message lives in while it is in flight.

TWO TIERS, AND WHY. A connection exists for as long as its host is connected, but it needs a large
buffer only while a large message is actually in flight -- and that is a much shorter thing. Giving
every connection a large buffer of its own for its whole life is what made a second interface cost
another 17 kB, for memory that is idle almost all of the time. So each one owns a small buffer
outright and borrows the large one, per message.

NOTHING HERE KNOWS ABOUT A TRANSPORT. It lived in `thp/memory_manager.py` until the V1 codec needed
the same two tiers for the WARD service interface, and that module cannot be imported in a codec
build at all -- it reaches for `trezorthp`. The classes themselves never did.
"""

from micropython import const

from trezor import loop, wire

# Reserve 8.5 kB. AuthenticityProof requires about 8500 bytes.
PROTOBUF_BUFFER_SIZE = const(8704)

# WHAT A CONNECTION HOLDS FOR ITSELF, for the whole time it exists. Every message small enough to
# fit rides on it and never touches the shared buffer, so this size decides how often two live
# connections can contend at all -- not what the protocol can carry, which is the shared buffer's
# size.
#
# Chosen to cover ordinary traffic: the THP handshake never comes near a Python buffer (the Rust
# channel has its own fixed handshake buffers), and the wallet messages a device sends and receives
# by the thousand -- Features, Success, PublicKey, Address, the signing exchanges -- are all a few
# hundred bytes. So the shared buffer is reached for by the rare large message and by nothing else.
SMALL_BUFFER_SIZE = const(1024)

if __debug__:
    from trezor import log


class WireBuffer:
    def __init__(self, size: int = PROTOBUF_BUFFER_SIZE) -> None:
        # Sized so a second interface can be given buffers of its own without paying twice for
        # the default. `get()` refuses anything larger, so the size a buffer is created with is a
        # protocol bound on whatever travels through it -- not merely a memory tuning knob.
        self.buf = memoryview(bytearray(size))

    def get(self, length: int) -> memoryview:
        assert length >= 0
        if length > len(self.buf):
            if __debug__:
                log.warning(
                    __name__,
                    "Failed to get a buffer - requested length (%d) is too big.",
                    length,
                )
            raise wire.FirmwareError("Failed to get a sufficiently large buffer")
        return self.buf[:length]


class SharedBuffer:
    """The one large buffer several connections borrow, held by at most one message at a time.

    WHY IT IS SAFE THAT THE WALLET AND THE SERVICE SHARE ONE. A WARD RPC is serialised inside a
    wallet workflow: the large wallet request has been decoded before the RPC begins and the large
    wallet response is encoded after it ends, so the two never need the buffer at the same instant
    even though both connections are alive throughout.

    AND WHERE THAT IS NOT ENOUGH. Under THP nothing enforces the serialisation -- `should_read`
    keeps every interface's read loop awake while any channel expects a message, so a new wallet
    message can start arriving mid-RPC. That is why this hands out a refusal rather than assuming:
    the loser is told, and THP already knows what to do about being told.
    """

    def __init__(self, size: int = PROTOBUF_BUFFER_SIZE) -> None:
        self.buf = memoryview(bytearray(size))
        # The source currently holding it, or None. Identity rather than a count: a lease is held by
        # one message of one connection, and "released by someone who never held it" is a bug worth
        # not papering over.
        self.holder: BufferSource | None = None
        # ONE MAILBOX PER SOURCE, NOT ONE FOR THE BUFFER. `loop.mailbox` asserts a single taker, so
        # a shared box would blow up the moment two connections waited on it at once -- which is
        # precisely the situation being waited for.
        self._waiters: list[loop.mailbox[None]] = []

    def add_waiter(self, box: "loop.mailbox[None]") -> None:
        self._waiters.append(box)

    def acquire(self, holder: "BufferSource") -> bool:
        if self.holder is not None and self.holder is not holder:
            return False
        self.holder = holder
        return True

    def release(self, holder: "BufferSource") -> None:
        if self.holder is not holder:
            return
        self.holder = None
        for box in self._waiters:
            # `replace=True` because a waiter already woken does not need waking twice, and a value
            # left in an unattended box is what makes a later waiter retry immediately rather than
            # sleep through a release that already happened.
            box.put(None, replace=True)


class BufferSource:
    """Where one direction of one connection gets the memory for the message currently in flight.

    Two tiers: a small buffer this connection owns outright, and a large one it borrows. Which tier
    a message lands in is decided by its size and by nothing else, so the caller asks for a length
    exactly as it did when this was a single `WireBuffer`.

    THE LEASE IS PER MESSAGE, NOT PER CONNECTION. That is the whole point, and it is why `release`
    is something callers have to remember: a lease held past the message that needed it is
    indistinguishable from the per-connection ownership this replaced.
    """

    def __init__(self, small: WireBuffer, shared: SharedBuffer) -> None:
        self._small = small
        self._shared = shared
        # Length handed out so far for the message in flight, so a grow can carry the prefix over.
        self._length = 0
        self._promoted = False
        self._wakeup: loop.mailbox[None] = loop.mailbox()
        shared.add_waiter(self._wakeup)

    def try_get(self, length: int) -> memoryview | None:
        """The buffer for the message in flight, or None if the shared one is taken.

        Growing is expected: a receive buffer learns the real payload length from the initiation
        packet's header, after that packet's payload has already been written.
        """
        if length <= len(self._small.buf) and not self._promoted:
            self._length = length
            return self._small.get(length)

        # Checked BEFORE acquiring, so a message too large for even the shared buffer does not
        # leave a lease behind on its way out.
        if length > len(self._shared.buf):
            if __debug__:
                log.warning(
                    __name__,
                    "Failed to get a buffer - requested length (%d) is too big.",
                    length,
                )
            raise wire.FirmwareError("Failed to get a sufficiently large buffer")

        if not self._shared.acquire(self):
            return None

        buf = self._shared.buf[:length]
        if not self._promoted:
            # THE PREFIX MUST SURVIVE THE MOVE. The Rust reassembler keeps offsets into the buffer
            # and re-verifies the CRC over the whole of it at the end, so the bytes written before
            # the grow have to still be there afterwards. When both tiers were slices of one
            # bytearray this was free; across two backing stores it has to be done.
            buf[: self._length] = self._small.buf[: self._length]
            self._promoted = True
        self._length = length
        return buf

    async def get_when_available(self, length: int) -> memoryview:
        """Like `try_get`, but waits for the shared buffer instead of refusing.

        For the sending side, where the alternative is failing a response the device has already
        decided to send. The read loop cannot use this -- it is not a coroutine and its answer to
        "not now" is TRANSPORT_BUSY, which is a thing the host retransmits through.

        Unbounded on purpose: `Channel.write` is already under the interface's write timeout, and a
        second timeout here would only decide the same thing twice, in the wrong place.
        """
        while True:
            buf = self.try_get(length)
            if buf is not None:
                return buf
            if __debug__:
                log.debug(__name__, "waiting for the shared wire buffer")
            await self._wakeup

    def release(self) -> None:
        """Give the shared buffer back. Idempotent, and safe on a source that never borrowed it."""
        self._promoted = False
        self._length = 0
        self._shared.release(self)

    def holds_shared(self) -> bool:
        return self._promoted
