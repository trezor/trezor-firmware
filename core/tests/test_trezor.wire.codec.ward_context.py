# flake8: noqa: F403,F405
from common import *  # isort:skip

import struct

from trezor import protobuf, utils
from trezor.enums import MessageType
from trezor.messages import WardEntryAck, WardServiceFetch
from trezor.wire import DataError, FirmwareError
from trezor.wire.protocol_common import Message

if not utils.USE_THP:
    from mock_wire_interface import MockHID
    from trezor.wire.buffers import SharedBuffer, WireBuffer
    from trezor.wire.codec import ward_context as W
    from trezor.wire.codec.buffers import CodecBufferSource, private_source


def _encode(msg):
    buffer = bytearray(protobuf.encoded_length(msg))
    protobuf.encode(buffer, msg)
    return bytes(buffer)


def _as_message(msg):
    return Message(msg.MESSAGE_WIRE_TYPE, _encode(msg))


class _CountingSource:
    """A `CodecBufferSource` that remembers whether anyone gave its lease back."""

    def __init__(self, inner):
        self._inner = inner
        self.released = 0

    def capacity(self):
        return self._inner.capacity()

    def get(self, length):
        return self._inner.get(length)

    def holds_shared(self):
        return self._inner.holds_shared()

    def release(self):
        self.released += 1
        self._inner.release()


@unittest.skipUnless(
    not utils.USE_THP, "the codec service endpoint exists only in a codec build"
)
class TestWardCodecContext(unittest.TestCase):
    """The endpoint's own state: which memory a message lands in, and what it refuses to be."""

    def _context(self):
        shared = SharedBuffer(4096)
        bootstrap = private_source(512, 512)
        pooled = CodecBufferSource(WireBuffer(256), shared, 4096)
        return W.WardCodecContext(MockHID(), bootstrap, pooled), bootstrap, pooled

    def test_unsolicited_traffic_never_reaches_the_shared_buffer(self):
        """The reason there are two sources at all.

        An RPC reply is read inside a wallet workflow, which is the moment the shared buffer is
        free. Anything arriving with no RPC in flight has no such guarantee, so it must not be able
        to take the buffer a live workflow is about to need.
        """
        ctx, _bootstrap, pooled = self._context()

        ctx.rpc_in_flight = False
        # Larger than the pooled tier's own small buffer, so it WOULD have been promoted to the
        # shared one had the bootstrap tier not been the one answering.
        self.assertIsNot(ctx.buffers.get(300), None)
        self.assertFalse(pooled.holds_shared())

    def test_the_tier_is_chosen_when_the_message_arrives_not_when_the_read_starts(self):
        """The race that a flag consulted before the wait could not win.

        The reader spends its life parked in `read_from_wire`, holding whatever source it was
        given on the way in. So the object it holds has to be the one that changes its mind --
        the first RPC reply lands on a read that STARTED while the endpoint was idle, and
        unsolicited traffic can arrive after a reply is delivered but before the flag is cleared.
        Both directions are one question asked at the right moment.
        """
        ctx, bootstrap, pooled = self._context()

        # Exactly what a parked `read_from_wire` is holding.
        parked = ctx.buffers

        ctx.rpc_in_flight = False
        self.assertEqual(parked.capacity(), bootstrap.capacity())
        self.assertEqual(parked.max_message_size(), bootstrap.max_message_size())

        # The RPC starts. Nothing re-arms the read; the source answers differently.
        ctx.rpc_in_flight = True
        self.assertEqual(parked.capacity(), pooled.capacity())
        self.assertEqual(parked.max_message_size(), pooled.max_message_size())

        # And back, without having handed the reader a different object at any point.
        ctx.rpc_in_flight = False
        self.assertEqual(parked.capacity(), bootstrap.capacity())
        self.assertIs(ctx.buffers, parked)

    def test_a_lease_taken_during_an_rpc_goes_back_after_it(self):
        """`holds_shared`/`release` must follow the POOLED tier, not the active one.

        The lease is taken while the flag is set and given back after the answer has been
        decoded, by which time the flag is clear -- so a source that asked the ACTIVE tier would
        be asking the bootstrap tier, which borrows nothing, and would strand the shared buffer.
        """
        ctx, _bootstrap, pooled = self._context()

        ctx.rpc_in_flight = True
        self.assertIsNot(ctx.buffers.get(2000), None)
        self.assertTrue(ctx.buffers.holds_shared())

        ctx.rpc_in_flight = False
        self.assertTrue(ctx.buffers.holds_shared())
        ctx.buffers.release()
        self.assertFalse(pooled.holds_shared())

    def test_it_carries_what_a_service_link_is_read_for(self):
        """`apps.ward.service._rpc` logs and tears down through these on EITHER transport.

        Written after the fact, and worth saying why: the unit tests for `_rpc` stub the link with
        a fake that defined `channel_id` because a THP `Channel` has one -- so the fake was more
        capable than the real object, and the first thing to notice was a device test failing with
        `'WardCodecContext' object has no attribute channel_id`. `Context` DECLARES `channel_id`
        without defining it, so inheriting the base class is not enough to have one.
        """
        ctx, _bootstrap, _pooled = self._context()

        self.assertEqual(ctx.channel_id, 0)
        self.assertTrue(ctx.iface is not None)

    def test_the_endpoint_has_no_session(self):
        """`wardd` must not create or activate a protocol-v1 wallet session.

        Inherited silently, `CodecContext.cache` would hand out `storage.cache_codec`'s active
        session -- which is the WALLET's. Every derivation a WARD operation needs happens in the
        workflow that called the service, so there is nothing this end should be able to reach.
        """
        ctx, _bootstrap, _pooled = self._context()
        with self.assertRaises(RuntimeError):
            ctx.cache


class _ExplodingSource:
    """A source that throws something the reader was never taught to expect, once."""

    def __init__(self, inner, exc):
        self._inner = inner
        self._exc = exc
        self.armed = True

    def capacity(self):
        return self._inner.capacity()

    def max_message_size(self):
        return self._inner.max_message_size()

    def get(self, length):
        if self.armed:
            self.armed = False
            raise self._exc
        return self._inner.get(length)

    def holds_shared(self):
        return self._inner.holds_shared()

    def release(self):
        self._inner.release()


@unittest.skipUnless(
    not utils.USE_THP, "the codec service endpoint exists only in a codec build"
)
class TestWardCodecReaderSurvives(unittest.TestCase):
    """One bad message must not retire the endpoint for the rest of the session."""

    def setUp(self):
        self._real = W._CONTEXT

    def tearDown(self):
        W._CONTEXT = self._real

    def test_an_unexpected_exception_does_not_stop_the_reader(self):
        """`FirmwareError` and `MemoryError` are not `WireError`, and used to escape.

        The loop's `finally` clears `_CONTEXT`, so what looked like one refused message was in
        fact the end of the service interface: every WARD operation afterwards fails at
        `service_link()` until the next MicroPython session restart. A daemon must not be able to
        buy that by sending one message.
        """
        iface = MockHID()
        bootstrap = _ExplodingSource(
            private_source(512, 512), FirmwareError("no buffer for you")
        )
        pooled = CodecBufferSource(WireBuffer(256), SharedBuffer(4096), 4096)

        gen = W.handle_ward_codec_interface(iface, bootstrap, pooled)
        gen.send(None)  # parks on the first read
        self.assertIsNotNone(W._CONTEXT)

        # A header is enough: the source explodes as soon as the message asks for memory.
        header = b"?##" + struct.pack(">HL", MessageType.WardServiceOpen, 0)
        try:
            # Absorbed, and a refusal is queued: the reader is now parked on the write.
            iface.mock_read(header, gen)
            # One packet is enough for a `Failure`. After it the loop goes back to reading.
            gen.send(iface.TX_PACKET_LEN)
        except StopIteration:
            self.fail("the reader stopped on an exception it should have absorbed")
        except Exception as exc:
            self.fail("the exception escaped the reader: %s" % exc)

        self.assertIsNotNone(W._CONTEXT)
        self.assertFalse(bootstrap.armed)
        # It answered rather than going quiet.
        self.assertEqual(len(iface.data), 1)

        gen.close()

    def test_a_teardown_reaches_a_read_already_in_progress(self):
        """The hole this pair of mechanisms exists to close.

        A daemon that sends a header and then trickles keeps the reader inside that frame -- and
        the frame took the POOLED tier, because it began while an RPC was in flight. `tear_down`
        clears the flag and drops the mailbox, and before this could reach neither the reader nor
        the lease: the buffer stayed held until the next MicroPython session restart, and on a THP
        build it is the wallet's buffer too.
        """
        iface = MockHID()
        shared = SharedBuffer(4096)
        pooled = CodecBufferSource(WireBuffer(256), shared, 4096)

        gen = W.handle_ward_codec_interface(
            iface, private_source(512, 512), pooled
        )
        gen.send(None)
        ctx = W._CONTEXT
        assert ctx is not None

        # An RPC is in flight, so the frame below reads into the shared tier.
        ctx.rpc_in_flight = True
        # Bigger than the pooled tier's own small buffer, so it must borrow the shared one --
        # which is the buffer this whole test is about.
        big = 1024
        header = b"?##" + struct.pack(">HL", MessageType.WardEntryAck, big)
        iface.mock_read(header + b"\x00" * (64 - 9), gen)
        self.assertTrue(pooled.holds_shared())

        # The operation gives up. The daemon is still sending.
        W.tear_down("the WARD service did not answer")
        self.assertTrue(ctx._cancelled)

        iface.mock_read(b"?" + b"\x00" * 63, gen)

        # The lease is back, the reader is still serving, and the endpoint is still there.
        self.assertFalse(pooled.holds_shared())
        self.assertIsNotNone(W._CONTEXT)
        self.assertIsNotNone(CodecBufferSource(WireBuffer(0), shared).get(2048))

        # And the abandoned frame is not resumed: the flag was cleared for the next read, so the
        # reader is waiting for a header rather than for the rest of a message nobody wants.
        self.assertFalse(ctx._cancelled)

        gen.close()


@unittest.skipUnless(
    not utils.USE_THP, "the codec service endpoint exists only in a codec build"
)
class TestWardCodecExchange(unittest.TestCase):
    """One question, one answer, and what happens to the answers nobody asked for."""

    def setUp(self):
        self._real = W._CONTEXT
        shared = SharedBuffer(4096)
        self.pooled = _CountingSource(CodecBufferSource(WireBuffer(256), shared))
        self.ctx = W.WardCodecContext(MockHID(), private_source(512), self.pooled)
        W._CONTEXT = self.ctx

        self.written = []

        async def _write(msg):
            self.written.append(msg)

        self.ctx.write = _write

    def tearDown(self):
        W._CONTEXT = self._real

    def _park(self, request):
        """Step an exchange to where it waits on the reader, the way the loop would.

        `await_result` cannot do this: it drives a task to completion, and the whole point of the
        mailbox is that the workflow STOPS here until the reader has something. And the answer
        cannot simply be parked in advance either -- `exchange` drains the box first, precisely so
        an answer to a question that already gave up cannot become this one's.
        """
        gen = W.exchange(request)
        box = gen.send(None)
        self.assertIs(box, self.ctx.reply)
        # In flight for as long as it is parked, which is what tells the reader where to route.
        self.assertTrue(self.ctx.rpc_in_flight)
        return gen

    def _finish(self, gen, value):
        """Hand the parked exchange what the reader put in the box.

        `loop._step` throws a value that is an exception and sends anything else; both are what a
        real reader can produce, so both are driven the same way here.
        """
        try:
            if isinstance(value, BaseException):
                gen.throw(value)
            else:
                gen.send(value)
        except StopIteration as e:
            return e.value
        raise AssertionError("the exchange did not finish")

    def test_the_request_goes_out_and_the_answer_comes_back(self):
        request = WardServiceFetch(entry_key=b"\x01" * 32)
        gen = self._park(request)

        answer = self._finish(gen, _as_message(WardEntryAck()))

        self.assertEqual(self.written, [request])
        self.assertEqual(answer.type, WardEntryAck.MESSAGE_WIRE_TYPE)
        # ...and the endpoint is ready for the next question rather than still mid-conversation
        self.assertFalse(self.ctx.rpc_in_flight)

    def test_an_exception_in_the_mailbox_is_raised_at_the_caller(self):
        """How a mangled frame fails the operation AT ONCE rather than at its deadline.

        The reader cannot answer a request nobody made -- the device is the initiator here -- so it
        puts what it caught where the workflow is already waiting.
        """
        gen = self._park(WardServiceFetch(entry_key=b"\x01" * 32))

        with self.assertRaises(DataError):
            self._finish(gen, DataError("bad frame"))

        self.assertFalse(self.ctx.rpc_in_flight)

    def test_a_second_question_in_flight_is_refused(self):
        """One stream and no request ids: two questions would make the two answers
        indistinguishable. A hard error rather than a queue, because queueing would be inventing a
        protocol the daemon does not speak."""
        self.ctx.rpc_in_flight = True

        with self.assertRaises(DataError):
            await_result(W.exchange(WardServiceFetch(entry_key=b"\x01" * 32)))

    def test_the_flag_is_cleared_even_when_the_write_fails(self):
        """Otherwise the reader would keep routing into a mailbox nobody reads, and the interface
        would never bootstrap again -- a service that is gone with nothing to say so."""

        async def _boom(msg):
            raise DataError("no")

        self.ctx.write = _boom

        with self.assertRaises(DataError):
            await_result(W.exchange(WardServiceFetch(entry_key=b"\x01" * 32)))

        self.assertFalse(self.ctx.rpc_in_flight)

    def test_a_stale_answer_is_dropped_and_its_lease_given_back(self):
        """An answer to a question that already gave up must not become the NEXT question's.

        The reader had read it and put it where nobody was waiting; it holds a receive lease, so
        dropping it silently would strand the shared buffer as well as confuse the conversation.
        """
        self.ctx.reply.put(Message(WardEntryAck.MESSAGE_WIRE_TYPE, b"", self.pooled))

        gen = self._park(WardServiceFetch(entry_key=b"\x01" * 32))
        # Dropped on the way in, not left to be mistaken for this question's answer.
        self.assertEqual(self.pooled.released, 1)

        answer = self._finish(gen, _as_message(WardEntryAck()))
        self.assertEqual(answer.type, WardEntryAck.MESSAGE_WIRE_TYPE)

    def test_tearing_down_frees_the_endpoint_to_be_bound_again(self):
        """No channel closes, and that is the point: the reader keeps reading, so a daemon that
        restarts announces itself and is heard. What has to go is the RPC flag and any answer that
        arrived too late to be anyone's."""
        self.ctx.rpc_in_flight = True
        self.ctx.reply.put(Message(WardEntryAck.MESSAGE_WIRE_TYPE, b"", self.pooled))

        W.tear_down("a test said so")

        self.assertFalse(self.ctx.rpc_in_flight)
        self.assertTrue(self.ctx.reply.is_empty())
        self.assertEqual(self.pooled.released, 1)

    def test_without_a_reader_there_is_nothing_to_ask(self):
        """Reachable for real: the reader is torn down and respawned on every MicroPython session
        restart, so this is a state an operation can meet. It fails the operation, not the
        firmware."""
        W._CONTEXT = None
        with self.assertRaises(DataError):
            W.service_link()


if __name__ == "__main__":
    unittest.main()
